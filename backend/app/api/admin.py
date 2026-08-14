from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Wallet, User, ExecutionLog
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    wallet_count = (await db.execute(select(func.count()).select_from(Wallet))).scalar() or 0
    active_count = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "active"))).scalar() or 0
    pending_count = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "pending"))).scalar() or 0
    rejected_count = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "rejected"))).scalar() or 0
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    trade_count = (await db.execute(select(func.count()).select_from(ExecutionLog))).scalar() or 0
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "totalWallets": wallet_count,
            "activeWallets": active_count,
            "pendingWallets": pending_count,
            "rejectedWallets": rejected_count,
            "totalUsers": user_count,
            "totalTrades": trade_count,
        },
        "jobs": {
            "discoveryInterval": "6h",
            "scoringInterval": "24h",
            "analysisInterval": "24h",
        },
        "services": {
            "backend": "ONLINE",
            "database": "CONNECTED",
            "listener": "UNKNOWN",
        }
    }

@router.get("/wallets")
async def get_all_wallets(
    status: str = None,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Wallet)
    if status:
        stmt = stmt.where(Wallet.status == status)
    stmt = stmt.order_by(Wallet.first_seen_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    wallets = result.scalars().all()
    return [{
        "address": w.address,
        "status": w.status,
        "tier": w.tier,
        "baleenScore": w.baleen_score,
        "winRatePct": w.win_rate_pct,
        "allTimePnlUsd": w.all_time_pnl_usd,
        "avgTradesPerDay": w.avg_trades_per_day,
        "totalTradesAnalyzed": w.total_trades_analyzed,
        "maxDrawdownPct": w.max_drawdown_pct,
        "rejectionReason": w.rejection_reason,
        "aiSummary": w.ai_summary,
        "aiStyleTag": w.ai_style_tag,
        "dormant": w.dormant,
        "firstSeenAt": w.first_seen_at.isoformat() if w.first_seen_at else None,
        "lastScoredAt": w.last_scored_at.isoformat() if w.last_scored_at else None,
    } for w in wallets]
