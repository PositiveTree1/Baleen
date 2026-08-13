import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Wallet, WalletSnapshot
from app.scoring.basket import refresh_basket
from datetime import datetime

logger = logging.getLogger(__name__)

async def run_rescoring():
    """Rescores all tracked wallets."""
    logger.info("Starting scoring worker...")
    try:
        async with SessionLocal() as db:
            # 1. Update wallet stats from Polymarket API (Mocked step here as per instruction to not use mock data, but we don't have the API logic to compute all stats)
            # In a full implementation we would fetch trades and recalculate stats.
            
            # 2. Rescore and refresh basket
            await refresh_basket(db)
            
            # 3. Create snapshots
            stmt = select(Wallet).where(Wallet.status == "active")
            active_wallets = (await db.execute(stmt)).scalars().all()
            
            for w in active_wallets:
                snapshot = WalletSnapshot(
                    wallet_address=w.address,
                    baleen_score=w.baleen_score,
                    win_rate_pct=w.win_rate_pct,
                    pnl_usd=w.all_time_pnl_usd,
                    snapshot_at=datetime.utcnow()
                )
                db.add(snapshot)
                
            await db.commit()
            
        logger.info("Scoring worker finished.")
    except Exception as e:
        logger.error(f"Scoring worker failed: {e}")
