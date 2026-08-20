from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Wallet
from app.scoring.engine import score_wallet
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def compute_baleen_score(stats: dict) -> float:
    """
    Computes Baleen Score (0 - 100) incorporating Multi-Horizon Consistency (1d, 2d, 3d, 7d).
    - PnL Score: up to 30 points
    - Win Rate Score: up to 30 points
    - Multi-Horizon Consistency Factor: up to 25 points (1-day, 2-day, 3-day, 7-day rolling wins)
    - Drawdown Shield: up to 15 points
    """
    pnl = stats.get('all_time_pnl_usd', 0) or 0
    win_rate = stats.get('win_rate_pct', 0) or 0
    drawdown = stats.get('max_drawdown_pct', 100) or 100
    daily_history = stats.get('daily_pnl_history') or []

    # 1. Base PnL & Win Rate
    pnl_score = min(max(0.0, pnl) / 500000.0, 1.0) * 30.0  # up to 30 points
    wr_score = min(max(0.0, win_rate) / 100.0, 1.0) * 30.0  # up to 30 points  
    dd_score = max(1.0 - drawdown / 40.0, 0.0) * 15.0      # up to 15 points

    # 2. Multi-Horizon Consistency Evaluation (1d, 2d, 3d, 7d)
    if daily_history and len(daily_history) >= 3:
        # Extract net daily PnL values
        nets = [float(h.get('net_pnl') or h.get('daily_pnl') or 0.0) for h in daily_history]
        
        # 1-day win ratio
        pos_1d = sum(1 for n in nets if n > 0)
        tot_1d = sum(1 for n in nets if n != 0) or 1
        r_1d = pos_1d / tot_1d

        # 3-day rolling window win ratio
        r_3d_wins = 0
        r_3d_tot = 0
        for i in range(len(nets) - 2):
            r_3d_tot += 1
            if sum(nets[i:i+3]) > 0:
                r_3d_wins += 1
        r_3d = (r_3d_wins / r_3d_tot) if r_3d_tot > 0 else r_1d

        # 7-day rolling window win ratio
        r_7d_wins = 0
        r_7d_tot = 0
        for i in range(len(nets) - 6):
            r_7d_tot += 1
            if sum(nets[i:i+7]) > 0:
                r_7d_wins += 1
        r_7d = (r_7d_wins / r_7d_tot) if r_7d_tot > 0 else r_3d

        consistency_factor = (r_1d * 0.35) + (r_3d * 0.35) + (r_7d * 0.30)
    else:
        # Fallback to win rate approximation if history is short
        consistency_factor = min(1.0, (win_rate / 100.0) * 0.85)

    consistency_score = round(consistency_factor * 25.0, 1)

    total_score = pnl_score + wr_score + dd_score + consistency_score
    return round(min(100.0, max(0.0, total_score)), 1)

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
            'is_hft': wallet.is_hft,
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
