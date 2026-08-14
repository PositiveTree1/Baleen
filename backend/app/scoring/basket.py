from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Wallet
from app.scoring.engine import score_wallet
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def compute_baleen_score(stats: dict) -> float:
    pnl = stats.get('all_time_pnl_usd', 0) or 0
    win_rate = stats.get('win_rate_pct', 0) or 0
    drawdown = stats.get('max_drawdown_pct', 100) or 100
    pnl_score = min(pnl / 500000, 1.0) * 40  # up to 40 points
    wr_score = min(win_rate / 100, 1.0) * 40  # up to 40 points  
    dd_score = max(1.0 - drawdown / 50, 0) * 20  # up to 20 points
    return round(pnl_score + wr_score + dd_score, 1)

async def get_active_basket(db: AsyncSession) -> list[Wallet]:
    """Returns active, non-dormant wallets."""
    stmt = select(Wallet).where(
        Wallet.status == "active",
        Wallet.dormant == False
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def refresh_basket(db: AsyncSession):
    """
    Rescore all tracked wallets, update statuses.
    A wallet dropping below gold tier gets status='rejected'
    Dormant wallets stay active but excluded from N_active count (handled by get_active_basket).
    """
    stmt = select(Wallet).where(Wallet.status.in_(["active", "pending"]))
    result = await db.execute(stmt)
    wallets = result.scalars().all()

    for wallet in wallets:
        stats = {
            'all_time_pnl_usd': wallet.all_time_pnl_usd,
            'avg_trades_per_day': wallet.avg_trades_per_day,
            'outlier_concentration_pct': wallet.outlier_concentration_pct,
            'win_rate_pct': wallet.win_rate_pct,
            'max_drawdown_pct': wallet.max_drawdown_pct,
        }
        
        # Only valid stats should be scored
        if stats['all_time_pnl_usd'] is None:
            continue
            
        score_res = score_wallet(stats)
        
        wallet.status = score_res.status
        wallet.tier = score_res.tier
        wallet.rejection_reason = score_res.rejection_reason
        wallet.baleen_score = compute_baleen_score(stats)
        wallet.last_scored_at = datetime.utcnow()

    await db.commit()
