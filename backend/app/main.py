from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import init_db, get_db
from app.api import wallets, execution_logs, users, admin
from app.workers.discovery_worker import run_discovery
from app.workers.scoring_worker import run_rescoring
from app.workers.analysis_worker import run_analysis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Baleen Backend", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wallets.router)
app.include_router(execution_logs.router)
app.include_router(users.router)
app.include_router(admin.router)

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    # Init DB
    await init_db()
    
    # Schedule workers
    scheduler.add_job(run_discovery, 'interval', hours=6, id='discovery_job')
    
    # Rescoring runs every 24 hours
    async def nightly_job():
        await run_rescoring()
        await run_analysis()
        
    scheduler.add_job(nightly_job, 'interval', hours=24, id='nightly_job')
    scheduler.start()
    logger.info("Scheduler started.")
    
    # Run discovery immediately on startup so we have data right away
    import asyncio
    asyncio.create_task(run_discovery())
    logger.info("Initial discovery run triggered.")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    from app.models import Wallet, ExecutionLog
    from sqlalchemy import func
    
    wallet_count = (await db.execute(
        select(func.count()).select_from(Wallet).where(Wallet.status == "active")
    )).scalar() or 0
    
    total_volume = (await db.execute(
        select(func.coalesce(func.sum(ExecutionLog.notional_usd), 0))
    )).scalar() or 0
    
    return {
        "totalVolumeMirrored": round(total_volume, 2),
        "activeBasketWhales": wallet_count,
        "indexerStatus": "ONLINE"
    }

@app.get("/api/diagnostics")
async def diagnostics(db: AsyncSession = Depends(get_db)):
    """Test all external API connections and report results."""
    import httpx
    from app.models import Wallet, User
    results = {}
    
    # Test Polymarket Data API
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in [
            ("polymarket_leaderboard", "https://data-api.polymarket.com/leaderboard"),
            ("polymarket_trades", "https://data-api.polymarket.com/trades"),
            ("gamma_markets", "https://gamma-api.polymarket.com/markets"),
        ]:
            try:
                res = await client.get(url, params={"limit": 2})
                data = res.json()
                if isinstance(data, list) and data:
                    results[name] = {"status": "OK", "count": len(data), "sample_keys": list(data[0].keys())[:10]}
                elif isinstance(data, dict):
                    results[name] = {"status": "OK", "type": "dict", "keys": list(data.keys())[:10]}
                else:
                    results[name] = {"status": "EMPTY", "raw": str(data)[:100]}
            except Exception as e:
                results[name] = {"status": "ERROR", "error": str(e)[:200]}
    
    # Test database
    try:
        wallet_count = (await db.execute(select(func.count()).select_from(Wallet))).scalar()
        user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
        results["database"] = {"status": "OK", "wallets": wallet_count, "users": user_count}
    except Exception as e:
        results["database"] = {"status": "ERROR", "error": str(e)[:200]}
    
    # Test scheduler
    jobs = [{"id": job.id, "next_run": str(job.next_run_time)} for job in scheduler.get_jobs()]
    results["scheduler"] = {"jobs": jobs}
    
    return results

@app.get("/")
async def root():
    return {"message": "Welcome to Baleen API"}
