"""Recover acknowledged listener work using PostgreSQL transaction ownership.

The claim lock is held until processing finishes; a killed worker releases it.
The consumer separately serializes and commits its effects. This deliberately
uses two connections, so a worker pool must provide at least two connections.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, or_
from app.database import SessionLocal
from app.models import SignalInbox, CanonicalSourceEvent

logger = logging.getLogger(__name__)
_local_worker = asyncio.Lock()


async def drain_signal_inbox(limit=25):
    from app.services.live_poller import live_trade_mirror
    if _local_worker.locked():
        return
    async with _local_worker:
        for _ in range(limit):
            async with SessionLocal() as db:
                # Retry state persists across restarts. Exhausted failures remain
                # visible for diagnosis instead of disappearing from the inbox.
                stmt = select(SignalInbox).where(SignalInbox.status == 'PENDING',
                    or_(SignalInbox.retry_at.is_(None), SignalInbox.retry_at <= datetime.utcnow())).order_by(
                    SignalInbox.received_at).limit(1).with_for_update(skip_locked=True)
                row = (await db.execute(stmt)).scalar_one_or_none()
                if row is None:
                    return
                p = row.payload
                if p.get('isMaker') is False:
                    row.status = 'QUARANTINED'
                    row.error_detail = 'Counterparty attribution is not an owned order fill; replay the wallet-owned receipt log'
                    row.processed_at = datetime.utcnow()
                    await db.commit()
                    continue
                if p.get('amountUnit') != 'raw_6':
                    row.status = 'QUARANTINED'
                    row.error_detail = 'Legacy payload has ambiguous quantity units; reconcile with receipt before replay'
                    row.processed_at = datetime.utcnow()
                    await db.commit()
                    continue
                try:
                    await live_trade_mirror.process_onchain_signal(
                        wallet_address=p['walletAddress'], side=p['side'], asset_id=p['assetId'],
                        amount_filled=p['amountFilled'], price_str=p['price'],
                        tx_hash=p['transactionHash'], log_index=p['logIndex'],
                        block_number=p['blockNumber'], timestamp_ms=p.get('timestamp'),
                        emitting_contract=p.get('contractAddress'), block_hash=p.get('blockHash'))
                    canonical = (await db.execute(select(CanonicalSourceEvent).where(
                        CanonicalSourceEvent.tx_hash == p['transactionHash'],
                        CanonicalSourceEvent.log_index == p['logIndex'],
                        CanonicalSourceEvent.source_wallet_address == p['walletAddress']).limit(1))).scalar_one_or_none()
                    row.status = 'QUARANTINED' if canonical and canonical.status in ('QUARANTINED', 'UNRESOLVED') else 'PROCESSED'
                    row.error_detail = None
                except Exception as exc:
                    row.attempts = (row.attempts or 0) + 1
                    row.status = 'FAILED' if row.attempts >= 10 else 'PENDING'
                    row.retry_at = datetime.utcnow() + timedelta(seconds=min(60, 2 ** row.attempts))
                    row.error_detail = str(exc)[:1000]
                    logger.exception('Signal inbox processing failed: %s', row.id)
                row.processed_at = datetime.utcnow()
                await db.commit()
