import logging
from app.database import SessionLocal
from app.services.wallet_shadow import capture_research_batch

logger = logging.getLogger(__name__)


async def run_shadow_observations():
    try:
        async with SessionLocal() as db:
            await capture_research_batch(db)
    except Exception:
        logger.exception("Forward wallet observation failed; no orders were submitted")
