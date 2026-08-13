from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import ExecutionLog

router = APIRouter(prefix="/api/execution-logs", tags=["execution_logs"])

@router.get("")
async def get_execution_logs(
    user_id: str,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExecutionLog).where(ExecutionLog.user_id == user_id)
    
    if status:
        stmt = stmt.where(ExecutionLog.status == status)
    if start_date:
        stmt = stmt.where(ExecutionLog.executed_at >= start_date)
    if end_date:
        stmt = stmt.where(ExecutionLog.executed_at <= end_date)
        
    stmt = stmt.order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    
    return result.scalars().all()
