import logging
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Wallet
from app.analysis.ai_summary import generate_summary

logger = logging.getLogger(__name__)

async def run_analysis():
    """Generates AI summaries for active wallets."""
    logger.info("Starting analysis worker...")
    try:
        async with SessionLocal() as db:
            stmt = select(Wallet).where(Wallet.status == "active")
            active_wallets = (await db.execute(stmt)).scalars().all()
            
            for w in active_wallets:
                stats = {
                    'win_rate_pct': w.win_rate_pct,
                    'all_time_pnl_usd': w.all_time_pnl_usd,
                    'avg_trades_per_day': w.avg_trades_per_day,
                    'max_drawdown_pct': w.max_drawdown_pct
                }
                
                summary, tag = await generate_summary(stats)
                if summary:
                    w.ai_summary = summary
                    w.ai_style_tag = tag
                    
            await db.commit()
            
        logger.info("Analysis worker finished.")
    except Exception as e:
        logger.error(f"Analysis worker failed: {e}")
