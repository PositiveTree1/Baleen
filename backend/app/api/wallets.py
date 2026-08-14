from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import Wallet, WalletSnapshot, ExecutionLog
from app.analysis.ai_summary import generate_summary
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wallets", tags=["wallets"])

def wallet_to_response(w: Wallet) -> dict:
    return {
        "address": w.address,
        "tier": w.tier or "standard",
        "win_rate_pct": w.win_rate_pct or 0.0,
        "all_time_pnl_usd": w.all_time_pnl_usd or 0.0,
        "avg_trades_per_day": w.avg_trades_per_day or 0.0,
        "baleen_score": w.baleen_score or 0.0,
        "ai_style_tag": w.ai_style_tag,
        "ai_summary": w.ai_summary,
        "max_drawdown_pct": w.max_drawdown_pct or 0.0,
        "status": w.status or "active",
        "dormant": bool(w.dormant),
        "total_trades_analyzed": w.total_trades_analyzed or 0,
        "rejection_reason": w.rejection_reason,
        "first_seen_at": w.first_seen_at.isoformat() if w.first_seen_at else None,
        "last_scored_at": w.last_scored_at.isoformat() if w.last_scored_at else None,
    }

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
        
    stmt = stmt.order_by(Wallet.baleen_score.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [wallet_to_response(w) for w in result.scalars().all()]

@router.get("/{address}")
async def get_wallet(address: str, db: AsyncSession = Depends(get_db)):
    clean_addr = address.lower()
    
    # Wallet query (case insensitive)
    stmt = select(Wallet).where(func.lower(Wallet.address) == clean_addr)
    wallet = (await db.execute(stmt)).scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    # Auto-generate AI summary on-demand if missing
    if not wallet.ai_summary or not wallet.ai_style_tag:
        try:
            stats_dict = {
                "win_rate_pct": wallet.win_rate_pct or 0.0,
                "all_time_pnl_usd": wallet.all_time_pnl_usd or 0.0,
                "avg_trades_per_day": wallet.avg_trades_per_day or 0.0,
                "max_drawdown_pct": wallet.max_drawdown_pct or 0.0,
            }
            ai_summary, ai_style_tag = await generate_summary(stats_dict)
            if ai_summary:
                wallet.ai_summary = ai_summary
            if ai_style_tag:
                wallet.ai_style_tag = ai_style_tag
            await db.commit()
            await db.refresh(wallet)
        except Exception as e:
            logger.warning(f"On-demand AI summary error for {clean_addr}: {e}")
            
    # Snapshots query
    snap_stmt = select(WalletSnapshot).where(
        func.lower(WalletSnapshot.wallet_address) == clean_addr
    ).order_by(WalletSnapshot.snapshot_at.asc()).limit(30)
    snapshots = (await db.execute(snap_stmt)).scalars().all()
    
    # Format score history
    score_history = []
    if snapshots:
        for s in snapshots:
            score_history.append({
                "snapshot_at": s.snapshot_at.isoformat() if s.snapshot_at else datetime.utcnow().isoformat(),
                "baleen_score": s.baleen_score or 0.0,
                "win_rate_pct": s.win_rate_pct or 0.0,
                "all_time_pnl_usd": s.all_time_pnl_usd or 0.0
            })
    else:
        # Default snapshot for chart if none recorded yet
        score_history.append({
            "snapshot_at": wallet.last_scored_at.isoformat() if wallet.last_scored_at else datetime.utcnow().isoformat(),
            "baleen_score": wallet.baleen_score or 75.0,
            "win_rate_pct": wallet.win_rate_pct or 0.0,
            "all_time_pnl_usd": wallet.all_time_pnl_usd or 0.0
        })
        
    # Recent trades query
    trade_stmt = select(ExecutionLog).where(
        func.lower(ExecutionLog.source_wallet_address) == clean_addr
    ).order_by(ExecutionLog.executed_at.desc()).limit(50)
    trades = (await db.execute(trade_stmt)).scalars().all()
    
    recent_trades = []
    for t in trades:
        recent_trades.append({
            "id": t.id,
            "market_id": t.market_id,
            "market_question": t.market_question,
            "side": t.side,
            "size_usd": t.size_usd,
            "fill_price": t.fill_price,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            "status": t.status,
            "pnl_usd": t.pnl_usd
        })
    
    return {
        "wallet": wallet_to_response(wallet),
        "score_history": score_history,
        "recent_trades": recent_trades
    }
