import asyncio
import logging
from app.database import SessionLocal
from app.discovery.scanner import scan_for_wallets
from app.scoring.basket import refresh_basket

logger = logging.getLogger(__name__)
_discovery_lock = asyncio.Lock()

async def run_discovery():
    """Runs one discovery scan; overlapping scheduler and user requests coalesce."""
    if _discovery_lock.locked():
        logger.info("Discovery request coalesced with an already-running scan.")
        return None
    async with _discovery_lock:
        logger.info("Starting discovery worker...")
        try:
            async with SessionLocal() as db:
                new_count = await scan_for_wallets(db)
            # scan_for_wallets owns the long-running discovery work. Do not
            # retain its database session while the independent basket refresh
            # runs, otherwise the small production pool is needlessly pinned.
            async with SessionLocal() as db:
                await refresh_basket(db)
            logger.info(f"Discovered {new_count} new wallets.")

            logger.info("Discovery worker finished.")
            return new_count
        except Exception as e:
            logger.error(f"Discovery worker failed: {e}")
            return None
