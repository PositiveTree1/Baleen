from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import ExecutionLog

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
    
    if status:
        stmt = stmt.where(ExecutionLog.status == status)
    if start_date:
        stmt = stmt.where(ExecutionLog.executed_at >= start_date)
    if end_date:
        stmt = stmt.where(ExecutionLog.executed_at <= end_date)
        
    stmt = stmt.order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    
    def execution_log_to_response(log) -> dict:
        return {
            "id": str(log.id),
            "timestamp": log.executed_at.isoformat() if log.executed_at else None,
            "walletAddress": log.source_wallet_address,
            "marketQuestion": log.market_question,
            "side": log.side,
            "entryPrice": log.whale_entry_price,
            "fillPrice": log.user_fill_price,
            "size": log.notional_usd,
            "status": log.status,
            "pnl": log.realized_pnl_usd,
        }
    
    return [execution_log_to_response(log) for log in result.scalars().all()]
