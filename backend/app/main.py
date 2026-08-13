from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import init_db
from app.api import wallets, execution_logs, users
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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wallets.router)
app.include_router(execution_logs.router)
app.include_router(users.router)

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

@app.get("/")
async def root():
    return {"message": "Welcome to Baleen API"}
