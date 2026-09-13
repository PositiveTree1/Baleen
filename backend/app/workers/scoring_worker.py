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
            # Refresh evidence before selecting a roster; cached scores are not a rescore.
            from app.discovery.scanner import evaluate_pending_wallets
            wallets = (await db.execute(select(Wallet).where(Wallet.status.in_(['active', 'tracked', 'pending'])))).scalars().all()
            for wallet in wallets:
                wallet.status = 'pending'
            await db.commit()
            await evaluate_pending_wallets(db)
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
