from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Wallet
from app.scoring.engine import score_wallet
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def compute_baleen_score(stats: dict) -> float:
    """
    Computes Baleen Score (0 - 100) with Consistency as the dominant factor.
    - PnL Score: up to 15 points
    - Win Rate Score: up to 20 points
    - Multi-Horizon Consistency Factor: up to 40 points (1-day, 3-day, 7-day, 30-day rolling wins)
    - Drawdown Shield: up to 15 points
    - Trade Volume Confidence Bonus: up to 10 points
    """
    pnl = stats.get('all_time_pnl_usd', 0) or 0
    win_rate = stats.get('win_rate_pct', 0) or 0
    drawdown = stats.get('max_drawdown_pct', 100) or 100
    daily_history = stats.get('daily_pnl_history') or []
    trades_count = stats.get('trades_count', 0) or 0

    # 1. PnL Score (15 pts max) — proves profitability, but no longer dominant
    pnl_score = min(max(0.0, pnl) / 500000.0, 1.0) * 15.0

    # 2. Win Rate Score (20 pts max)
    wr_score = min(max(0.0, win_rate) / 100.0, 1.0) * 20.0

    # 3. Drawdown Shield (15 pts max) — rewards tight risk management
    dd_score = max(1.0 - drawdown / 40.0, 0.0) * 15.0

    # 4. Trade Volume Confidence Bonus (10 pts max)
    # Whales with 200+ resolved trades get full points; fewer trades = less confidence
    volume_score = min(trades_count / 200.0, 1.0) * 10.0

    # 5. Multi-Horizon Consistency Evaluation (40 pts max) — THE DOMINANT FACTOR
    if daily_history and len(daily_history) >= 3:
        nets = [float(h.get('net_pnl') or h.get('daily_pnl') or 0.0) for h in daily_history]

        # 1-day win ratio: what fraction of individual trading days are profitable?
        pos_1d = sum(1 for n in nets if n > 0)
        tot_1d = sum(1 for n in nets if n != 0) or 1
        r_1d = pos_1d / tot_1d

        # 3-day rolling window: are they profitable across every 3-day stretch?
        r_3d_wins = 0
        r_3d_tot = 0
        for i in range(len(nets) - 2):
            r_3d_tot += 1
            if sum(nets[i:i+3]) > 0:
                r_3d_wins += 1
        r_3d = (r_3d_wins / r_3d_tot) if r_3d_tot > 0 else r_1d

        # 7-day rolling window: are they profitable across every week?
        r_7d_wins = 0
        r_7d_tot = 0
        for i in range(len(nets) - 6):
            r_7d_tot += 1
            if sum(nets[i:i+7]) > 0:
                r_7d_wins += 1
        r_7d = (r_7d_wins / r_7d_tot) if r_7d_tot > 0 else r_3d

        # 30-day rolling window: are they profitable across every month?
        r_30d_wins = 0
        r_30d_tot = 0
        for i in range(len(nets) - 29):
            r_30d_tot += 1
            if sum(nets[i:i+30]) > 0:
                r_30d_wins += 1
        r_30d = (r_30d_wins / r_30d_tot) if r_30d_tot > 0 else r_7d

        consistency_factor = (r_1d * 0.20) + (r_3d * 0.25) + (r_7d * 0.30) + (r_30d * 0.25)
    else:
        # Fallback for whales with very short history — penalize lack of data
        consistency_factor = min(1.0, (win_rate / 100.0) * 0.65)

    consistency_score = round(consistency_factor * 40.0, 1)

    total_score = pnl_score + wr_score + dd_score + volume_score + consistency_score
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
