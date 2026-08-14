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

@app.get("/")
async def root():
    return {"message": "Welcome to Baleen API"}
