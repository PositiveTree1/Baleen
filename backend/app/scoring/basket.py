from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Wallet
from app.scoring.engine import score_wallet
import logging

logger = logging.getLogger(__name__)

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
        
        # If it drops below Gold tier (and was previously Gold), we can reject it
        if wallet.tier != "Gold Sniper" and wallet.status == "active":
             # We only support Gold Sniper for active tracking right now, based on requirements context
             # "A wallet dropping below gold tier gets status='rejected'"
             wallet.status = "rejected"
             wallet.rejection_reason = "DROPPED_BELOW_GOLD_TIER"
             wallet.tier = None

    await db.commit()
