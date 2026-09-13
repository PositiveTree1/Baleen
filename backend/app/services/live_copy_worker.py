"""Scheduled live copying; flag, account activation, grants and policy all gate I/O."""
import logging
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select, exists, cast, String, literal
from app.config import settings
from app.database import SessionLocal
from app.models import LiveExecutionAccount, LiveCopyPolicy, CanonicalSourceEvent, LiveOrderIntent, LiveSourcePosition
from app.services.live_runtime import live_runtime
from app.services.live_copy_coordinator import LiveCopyCoordinator
from app.services.live_market_evidence import LiveMarketEvidence
from app.services.settlement_receipts import PolygonSettlementReader

logger = logging.getLogger(__name__)


async def run_live_copy():
    if not settings.LIVE_EXECUTION_ENABLED or not settings.POLYGON_SETTLEMENT_RPC_URL:
        return
    async with SessionLocal() as db:
        if db.bind.dialect.name != 'postgresql':
            return
        ids = (await db.execute(select(LiveExecutionAccount.user_id).where(LiveExecutionAccount.enabled.is_(True)))).scalars().all()
    for uid in ids:
        try:
            async with SessionLocal() as db:
                account, policy = await db.get(LiveExecutionAccount, uid), await db.get(LiveCopyPolicy, uid)
                if account is None or policy is None:
                    continue
                held_sources = (await db.execute(select(LiveSourcePosition.source_wallet_address).where(
                    LiveSourcePosition.user_id == uid, LiveSourcePosition.quantity > 0))).scalars().all()
                since = max(policy.updated_at, datetime.utcnow()-timedelta(milliseconds=policy.limits['max_source_age_ms']))
                accounted = exists(select(LiveOrderIntent.id).where(LiveOrderIntent.user_id == uid,
                    LiveOrderIntent.run_id == account.run_id,
                    LiveOrderIntent.intent_key == literal('source:')+cast(CanonicalSourceEvent.id, String)))
                sources = (await db.execute(select(CanonicalSourceEvent.id).where(
                    CanonicalSourceEvent.source_wallet_address.in_(set(policy.source_wallets) | set(held_sources)),
                    CanonicalSourceEvent.block_time >= since, CanonicalSourceEvent.status.in_(['CONFIRMED','APPLIED']),
                    ~accounted).order_by(CanonicalSourceEvent.block_time, CanonicalSourceEvent.log_index).limit(100))).scalars().all()
                prepared = (await db.execute(select(LiveOrderIntent.risk_context).where(LiveOrderIntent.user_id == uid,
                    LiveOrderIntent.run_id == account.run_id, LiveOrderIntent.state == 'PREPARED'))).scalars().all()
                import uuid
                sources = [uuid.UUID(p['source_event_id']) for p in prepared if p] + list(sources)
            if not sources:
                continue
            async with live_runtime(SessionLocal, uid) as runtime, httpx.AsyncClient(
                    base_url=settings.POLYGON_SETTLEMENT_RPC_URL, timeout=10, follow_redirects=False) as rpc:
                coordinator = LiveCopyCoordinator(SessionLocal, runtime, LiveMarketEvidence(runtime.http, PolygonSettlementReader(rpc)))
                for source_id in sources:
                    try:
                        await coordinator.copy_source(uid, source_id)
                    except Exception as exc:
                        logger.warning('Live copy attempt stopped: %s', type(exc).__name__)
        except Exception as exc:
            logger.warning('Live copy account unavailable: %s', type(exc).__name__)
