from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import ExecutionLog
from app.services.mark_to_market import get_live_price, get_consensus_info

router = APIRouter(prefix="/api/executions", tags=["execution_logs"])

@router.get("")
async def get_execution_logs(
    user_id: Optional[str] = Query(None, alias="userId"),
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExecutionLog)
    if user_id:
        stmt = stmt.where(ExecutionLog.user_id == user_id)
    else:
        # System-wide live feed: show deduplicated system logs
        stmt = stmt.where(ExecutionLog.user_id.is_(None))
    
    if status:
        stmt = stmt.where(ExecutionLog.status == status)
    if start_date:
        stmt = stmt.where(ExecutionLog.executed_at >= start_date)
    if end_date:
        stmt = stmt.where(ExecutionLog.executed_at <= end_date)
        
    stmt = stmt.order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    
    def execution_log_to_response(log) -> dict:
        cid = log.market_condition_id or ""
        fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
        cur_p = get_live_price(cid, fill_p)
        consensus = get_consensus_info(cid)
        
        # Calculate dynamic PnL
        notional = float(log.notional_usd or 0.0)
        pnl = log.realized_pnl_usd
        if pnl is None and fill_p > 0:
            if log.side == "BUY":
                pnl = round(notional * ((cur_p - fill_p) / fill_p), 2)
            else:
                pnl = round(notional * ((fill_p - cur_p) / fill_p), 2)
        elif pnl is not None:
            pnl = round(pnl, 2)
            
        pnl_pct = round(((cur_p - fill_p) / fill_p) * 100.0, 1) if fill_p > 0 and log.side == "BUY" else round(((fill_p - cur_p) / fill_p) * 100.0, 1) if fill_p > 0 else 0.0

        return {
            "id": str(log.id),
            "timestamp": log.executed_at.isoformat() if log.executed_at else None,
            "walletAddress": log.source_wallet_address,
            "marketQuestion": log.market_question,
            "marketConditionId": cid,
            "side": log.side,
            "entryPrice": log.whale_entry_price,
            "fillPrice": log.user_fill_price,
            "currentPrice": cur_p,
            "size": log.notional_usd,
            "status": log.status,
            "pnl": pnl,
            "pnlPct": pnl_pct,
            "consensus": consensus,
            "polymarketUrl": f"https://polymarket.com/event/{cid}" if cid else "https://polymarket.com"
        }
    
    return [execution_log_to_response(log) for log in result.scalars().all()]
