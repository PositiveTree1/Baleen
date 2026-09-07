import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ExposureLedger
from app.config import settings
from app.services.event_logger import log_event

logger = logging.getLogger(__name__)

@dataclass
class NettedActionResult:
    action: str  # "WAIT" | "EXECUTE"
    order_size_usd: float
    side: str  # "BUY" | "SELL"
    virtual_position: float
    executed_position: float
    pending_usd: float
    ledger_id: Optional[str] = None
    reason: str = ""

async def get_or_create_ledger_entry(
    db: AsyncSession,
    wallet_address: str,
    condition_id: str,
    outcome: str,
    market_question: str = "",
    asset_id: str = "",
    whale_price: Optional[float] = None
) -> ExposureLedger:
    """Fetches active ledger entry or initializes a new one for (wallet, condition, outcome)."""
    norm_addr = wallet_address.lower()
    norm_cid = condition_id.lower()
    norm_outcome = outcome.strip().lower()

    stmt = select(ExposureLedger).where(
        func.lower(ExposureLedger.wallet_address) == norm_addr,
        func.lower(ExposureLedger.market_condition_id) == norm_cid,
        func.lower(ExposureLedger.outcome) == norm_outcome,
        ExposureLedger.status != "closed"
    ).limit(1)
    
    entry = (await db.execute(stmt)).scalars().first()
    if not entry:
        entry = ExposureLedger(
            id=uuid.uuid4(),
            wallet_address=wallet_address,
            market_condition_id=condition_id,
            outcome=outcome,
            asset_id=asset_id or None,
            virtual_position_usd=0.0,
            executed_position_usd=0.0,
            last_whale_price=whale_price,
            market_question=market_question or None,
            status="accumulating",
            last_updated_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        db.add(entry)
        await db.flush()

    return entry

async def update_intended_exposure(
    db: AsyncSession,
    wallet_address: str,
    condition_id: str,
    outcome: str,
    delta_usd: float,
    whale_price: float,
    market_question: str = "",
    asset_id: str = "",
    min_threshold_usd: float = 1.0
) -> NettedActionResult:
    """
    Updates the running virtual position for (wallet, condition, outcome).
    - If net pending delta >= min_threshold_usd ($1.00): triggers EXECUTE.
    - If net pending delta < min_threshold_usd: logs ACCUMULATING and returns WAIT.
    """
    entry = await get_or_create_ledger_entry(
        db=db,
        wallet_address=wallet_address,
        condition_id=condition_id,
        outcome=outcome,
        market_question=market_question,
        asset_id=asset_id,
        whale_price=whale_price
    )

    # 1. Update virtual intended position
    entry.virtual_position_usd = round(entry.virtual_position_usd + delta_usd, 4)
    entry.last_whale_price = whale_price
    entry.last_updated_at = datetime.utcnow()
    if market_question:
        entry.market_question = market_question
    if asset_id:
        entry.asset_id = asset_id

    # 2. Calculate net unexecuted pending exposure
    pending = round(entry.virtual_position_usd - entry.executed_position_usd, 4)

    # 3. Check if net pending crosses the order threshold ($1.00)
    if abs(pending) >= min_threshold_usd:
        side = "BUY" if pending > 0 else "SELL"
        order_size = round(abs(pending), 2)
        logger.info(
            f"🎯 Netted Exposure Threshold Crossed! Wallet={wallet_address[:8]}... "
            f"Market='{market_question[:30]}' Outcome='{outcome}' "
            f"Virtual=${entry.virtual_position_usd:.2f} Executed=${entry.executed_position_usd:.2f} "
            f"-> Placing {side} for ${order_size:.2f}"
        )
        return NettedActionResult(
            action="EXECUTE",
            order_size_usd=order_size,
            side=side,
            virtual_position=entry.virtual_position_usd,
            executed_position=entry.executed_position_usd,
            pending_usd=pending,
            ledger_id=str(entry.id),
            reason="THRESHOLD_CROSSED"
        )
    else:
        entry.status = "accumulating"
        await db.commit()
        logger.info(
            f"⏳ Netted Exposure Accumulating: Wallet={wallet_address[:8]}... "
            f"Market='{market_question[:30]}' Outcome='{outcome}' "
            f"Delta=${delta_usd:+.2f} -> Virtual=${entry.virtual_position_usd:.2f} "
            f"Pending=${pending:+.2f} (< ${min_threshold_usd:.2f}). Waiting for next trade or expiry."
        )
        import asyncio
        asyncio.create_task(log_event(
            "NET_EXPOSURE_ACCUMULATING",
            f"Sub-minimum exposure queued: {market_question[:50]}",
            detail=f"Scaled delta {delta_usd:+.2f} USD. Running virtual: ${entry.virtual_position_usd:.2f}, pending: ${pending:+.2f}. Status: accumulating.",
            severity="info",
            related_address=wallet_address,
            related_market=market_question,
        ))
        return NettedActionResult(
            action="WAIT",
            order_size_usd=0.0,
            side="BUY" if pending >= 0 else "SELL",
            virtual_position=entry.virtual_position_usd,
            executed_position=entry.executed_position_usd,
            pending_usd=pending,
            ledger_id=str(entry.id),
            reason="ACCUMULATING_SUB_MINIMUM"
        )

async def confirm_exposure_execution(
    db: AsyncSession,
    ledger_id: str,
    executed_delta: float,
    new_status: str = "executed"
) -> None:
    """Updates executed_position once an order has been successfully placed."""
    try:
        u_id = uuid.UUID(ledger_id)
        stmt = select(ExposureLedger).where(ExposureLedger.id == u_id)
        entry = (await db.execute(stmt)).scalars().first()
        if entry:
            entry.executed_position_usd = round(entry.executed_position_usd + executed_delta, 4)
            entry.status = new_status
            entry.last_updated_at = datetime.utcnow()
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to confirm exposure execution for ledger {ledger_id}: {e}")

async def check_and_flush_expired_entries(
    db: AsyncSession,
    expiry_hours: Optional[float] = None,
    expiry_behavior: Optional[str] = None,
    min_order_usd: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Scans for accumulating entries older than expiry_hours.
    - If behavior == 'flush': prepares order for execution at min_order_usd, updates status to 'flushed_on_expiry'.
    - If behavior == 'drop': resets virtual_position to executed_position, sets 'expired_unfilled'.
    """
    hours = expiry_hours if expiry_hours is not None else settings.NETTED_LEDGER_EXPIRY_HOURS
    behavior = (expiry_behavior if expiry_behavior is not None else settings.NETTED_LEDGER_EXPIRY_BEHAVIOR).lower()

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    stmt = select(ExposureLedger).where(
        ExposureLedger.status == "accumulating",
        ExposureLedger.last_updated_at <= cutoff
    )
    stale_entries = (await db.execute(stmt)).scalars().all()
    flushed_orders = []

    for entry in stale_entries:
        pending = round(entry.virtual_position_usd - entry.executed_position_usd, 4)
        if abs(pending) < 0.01:
            # Virtually flat already
            entry.status = "executed"
            continue

        if behavior == "flush":
            side = "BUY" if pending > 0 else "SELL"
            flush_size = max(min_order_usd, round(abs(pending), 2))
            flushed_orders.append({
                "ledger_id": str(entry.id),
                "wallet_address": entry.wallet_address,
                "market_condition_id": entry.market_condition_id,
                "outcome": entry.outcome,
                "asset_id": entry.asset_id,
                "market_question": entry.market_question,
                "side": side,
                "size_usd": flush_size,
                "pending_usd": pending,
                "virtual_position": entry.virtual_position_usd,
                "executed_position": entry.executed_position_usd,
                "last_whale_price": entry.last_whale_price,
            })
            entry.status = "flushed_on_expiry"
            entry.executed_position_usd = entry.virtual_position_usd
            entry.last_updated_at = datetime.utcnow()
            
            logger.info(
                f"⏰ Exposure Ledger Stale Flush: {entry.market_question} | "
                f"Pending=${pending:+.2f} -> Force Flushing {side} ${flush_size:.2f}."
            )
            import asyncio
            asyncio.create_task(log_event(
                "TRADE_FLUSHED_ON_EXPIRY",
                f"Expiry flush: {entry.market_question or 'Market'}",
                detail=f"Stale exposure ({hours}h). Flushed {side} for ${flush_size:.2f} (pending was ${pending:.2f}).",
                severity="info",
                related_address=entry.wallet_address,
                related_market=entry.market_question,
            ))
        else:
            # Drop and reset
            logger.info(
                f"🚫 Exposure Ledger Stale Drop: {entry.market_question} | "
                f"Dropping pending ${pending:+.2f} after {hours}h."
            )
            entry.virtual_position_usd = entry.executed_position_usd
            entry.status = "expired_unfilled"
            entry.last_updated_at = datetime.utcnow()

            import asyncio
            asyncio.create_task(log_event(
                "TRADE_EXPIRED_UNFILLED",
                f"Expiry drop: {entry.market_question or 'Market'}",
                detail=f"Stale exposure ({hours}h) dropped without trade. Virtual reset to executed: ${entry.executed_position_usd:.2f}.",
                severity="warning",
                related_address=entry.wallet_address,
                related_market=entry.market_question,
            ))

    if stale_entries:
        await db.commit()

    return flushed_orders

async def close_resolved_ledger_entries(
    db: AsyncSession,
    condition_id: str
) -> int:
    """Marks all ledger entries for a condition_id as closed upon market resolution."""
    stmt = select(ExposureLedger).where(
        func.lower(ExposureLedger.market_condition_id) == condition_id.lower(),
        ExposureLedger.status != "closed"
    )
    entries = (await db.execute(stmt)).scalars().all()
    count = len(entries)
    for e in entries:
        e.status = "closed"
        e.last_updated_at = datetime.utcnow()
    if entries:
        await db.commit()
        logger.info(f"Closed {count} exposure ledger entries for resolved market {condition_id[:12]}...")
    return count
