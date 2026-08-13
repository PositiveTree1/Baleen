import logging
from app.database import SessionLocal
from app.discovery.scanner import scan_for_wallets
from app.scoring.basket import refresh_basket

logger = logging.getLogger(__name__)

async def run_discovery():
    """Runs the full discovery scan."""
    logger.info("Starting discovery worker...")
    try:
        async with SessionLocal() as db:
            new_count = await scan_for_wallets(db)
            logger.info(f"Discovered {new_count} new wallets.")
            
            # Score pending wallets
            await refresh_basket(db)
            
        logger.info("Discovery worker finished.")
    except Exception as e:
        logger.error(f"Discovery worker failed: {e}")
