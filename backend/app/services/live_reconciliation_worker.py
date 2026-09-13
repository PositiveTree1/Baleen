"""Reconcile exchange state and durable stop requests, including disabled accounts.

Never submits an order. Cancellation targets only locally journaled order hashes.
"""
import logging
from datetime import datetime
import httpx
from sqlalchemy import select
from app.auth import decrypt_secret
from app.config import settings
from app.database import SessionLocal
from app.models import LiveExecutionAccount, LiveWalletLink, LiveReconciliation
from app.services.clob_gateway import ClobCredentials, ClobGateway, ExchangeAuthenticationError
from app.services.live_reconciliation import LiveReconciler

logger = logging.getLogger(__name__)


async def reconcile_live_accounts():
    async with SessionLocal() as db:
        if db.bind.dialect.name != 'postgresql':
            return
        links = (await db.execute(select(LiveWalletLink).join(
            LiveExecutionAccount, LiveExecutionAccount.user_id == LiveWalletLink.user_id))).scalars().all()
    for link in links:
        # No connection is created merely because a legacy credentials row exists.
        # An explicit live account is required; onboarding must verify its binding.
        try:
            async with SessionLocal() as db:
                account = await db.get(LiveExecutionAccount, link.user_id)
                if (account is None or not link.polymarket_wallet_address
                        or account.wallet_address.lower() != link.polymarket_wallet_address.lower()
                        or link.signature_type not in (0, 1, 2, 3)):
                    raise ValueError('Live account binding mismatch')
            credentials = ClobCredentials(link.signer_address or '', decrypt_secret(link.clob_api_key_enc),
                decrypt_secret(link.clob_api_secret_enc), decrypt_secret(link.clob_api_passphrase_enc))
            async with httpx.AsyncClient(base_url=settings.CLOB_API_URL, timeout=10, follow_redirects=False) as client:
                if settings.POLYGON_SETTLEMENT_RPC_URL:
                    from app.services.settlement_receipts import PolygonSettlementReader
                    async with httpx.AsyncClient(base_url=settings.POLYGON_SETTLEMENT_RPC_URL,
                                                 timeout=10, follow_redirects=False) as rpc:
                        await LiveReconciler(SessionLocal, PolygonSettlementReader(rpc)).reconcile(
                            link.user_id, ClobGateway(credentials, client), link.signature_type)
                else:
                    await LiveReconciler(SessionLocal).reconcile(link.user_id, ClobGateway(credentials, client), link.signature_type)
        except Exception as exc:
            # One damaged credential record must not starve every other account.
            # Never persist provider exception text, which may contain credentials.
            logger.error('Live reconciliation setup failed: %s', type(exc).__name__)
            async with SessionLocal() as db, db.begin():
                account = (await db.execute(select(LiveExecutionAccount).where(
                    LiveExecutionAccount.user_id == link.user_id).with_for_update())).scalar_one_or_none()
                if account is not None:
                    account.enabled, account.reconciled_at = False, None
                    db.add(LiveReconciliation(user_id=link.user_id, status='BLOCKED',
                        finished_at=datetime.utcnow(), detail='Reconciliation setup failed: ' + type(exc).__name__))
