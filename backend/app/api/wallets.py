from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.database import get_db
from app.models import Wallet, WalletSnapshot, ExecutionLog

router = APIRouter(prefix="/api/wallets", tags=["wallets"])

@router.get("")
async def list_wallets(
    tier: Optional[str] = None,
    dormant: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Wallet).where(Wallet.status == "active")
    
    if tier:
        stmt = stmt.where(Wallet.tier == tier)
    if dormant is not None:
        stmt = stmt.where(Wallet.dormant == dormant)
        
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    
    def wallet_to_response(w) -> dict:
        return {
            "address": w.address,
            "tier": w.tier,
            "win_rate_pct": w.win_rate_pct,
            "all_time_pnl_usd": w.all_time_pnl_usd,
            "avg_trades_per_day": w.avg_trades_per_day,
            "baleen_score": w.baleen_score,
            "ai_style_tag": w.ai_style_tag,
            "ai_summary": w.ai_summary,
            "max_drawdown_pct": w.max_drawdown_pct,
            "status": w.status,
            "dormant": w.dormant,
            "total_trades_analyzed": w.total_trades_analyzed,
            "rejection_reason": w.rejection_reason,
            "first_seen_at": w.first_seen_at.isoformat() if w.first_seen_at else None,
            "last_scored_at": w.last_scored_at.isoformat() if w.last_scored_at else None,
        }

    return [wallet_to_response(w) for w in result.scalars().all()]

@router.get("/{address}")
async def get_wallet(address: str, db: AsyncSession = Depends(get_db)):
    address = address.lower()
    # Wallet
    stmt = select(Wallet).where(Wallet.address == address)
    wallet = (await db.execute(stmt)).scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    # Snapshots
    snap_stmt = select(WalletSnapshot).where(WalletSnapshot.wallet_address == address).order_by(WalletSnapshot.snapshot_at.desc()).limit(30)
    snapshots = (await db.execute(snap_stmt)).scalars().all()
    
    # Recent trades
    trade_stmt = select(ExecutionLog).where(ExecutionLog.source_wallet_address == address).order_by(ExecutionLog.executed_at.desc()).limit(50)
    trades = (await db.execute(trade_stmt)).scalars().all()
    
    return {
        "wallet": wallet_to_response(wallet),
        "score_history": snapshots,
        "recent_trades": trades
    }
