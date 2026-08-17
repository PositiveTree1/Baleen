import asyncio
import logging
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
import time
import os
import httpx
from app.config import settings

server_start_time = time.time()
last_cron_ping_time = time.time()

async def keep_alive_job():
    """Pings the public endpoint every 5 minutes to prevent Render idle spin-down."""
    global last_cron_ping_time
    external_url = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("BACKEND_PUBLIC_URL")
        or getattr(settings, "BACKEND_URL", None)
        or "http://localhost:8000"
    ).rstrip("/")
    target = f"{external_url}/health"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(target)
            last_cron_ping_time = time.time()
            logger.info(f"Keep-alive public ping succeeded: {target} (status {resp.status_code})")
    except Exception as e:
        logger.warning(f"Keep-alive ping error to {target}: {e}")
        last_cron_ping_time = time.time()

@app.on_event("startup")
async def startup_event():
    # Init DB
    await init_db()

    # Ensure initial VIP whales are present if database is empty (e.g. after fresh container deploy)
    from app.models import Wallet
    from app.database import SessionLocal
    async with SessionLocal() as db:
        cnt = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "active"))).scalar() or 0
        if cnt == 0:
            logger.info("Fresh database detected on startup. Auto-seeding initial VIP Alpha Whales...")
            vip_wallets = [
                Wallet(
                    address="0x6d9fc316fcb1e1fb33c2a6ae1d2cfcfc7cbabfa1",
                    status="active",
                    tier="gold_sniper",
                    all_time_pnl_usd=299000.0,
                    win_rate_pct=84.5,
                    baleen_score=95.0,
                    ai_style_tag="Macro Whale",
                    ai_summary="Titan VIP: Systematic macro & geopolitical resolution sniper with strong historical alpha.",
                    avg_trades_per_day=4.2,
                    trades_per_hour=0.4,
                    wilson_lb=78.0,
                    alpha_per_trade=310.0,
                    profit_factor=3.8
                ),
                Wallet(
                    address="0x63ce3421c640a44e59feedb93f18e97a3cf53549",
                    status="active",
                    tier="gold_sniper",
                    all_time_pnl_usd=2210000.0,
                    win_rate_pct=79.2,
                    baleen_score=98.0,
                    ai_style_tag="Mega Whale",
                    ai_summary="Titan VIP: High-notional institutional market leader with $2.2M+ lifetime PnL.",
                    avg_trades_per_day=6.5,
                    trades_per_hour=0.8,
                    wilson_lb=74.0,
                    alpha_per_trade=450.0,
                    profit_factor=4.2
                ),
                Wallet(
                    address="0x1cc16713915be5cfef36cb1e85f09623e110ec43",
                    status="active",
                    tier="gold_sniper",
                    all_time_pnl_usd=185000.0,
                    win_rate_pct=88.0,
                    baleen_score=92.0,
                    ai_style_tag="Sniper Whale",
                    ai_summary="Titan VIP: Wickier - High precision tactical event trader with 88% win rate.",
                    avg_trades_per_day=3.8,
                    trades_per_hour=0.3,
                    wilson_lb=81.0,
                    alpha_per_trade=220.0,
                    profit_factor=3.5
                ),
                Wallet(
                    address="0xdf17f4a86b3cc76ab943c3328eb9f8c6ebf242c7",
                    status="active",
                    tier="gold_sniper",
                    all_time_pnl_usd=340000.0,
                    win_rate_pct=82.1,
                    baleen_score=94.0,
                    ai_style_tag="Alpha Whale",
                    ai_summary="Titan VIP: Clear-Corridor - Deep liquidity political & cultural market specialist.",
                    avg_trades_per_day=5.1,
                    trades_per_hour=0.5,
                    wilson_lb=76.0,
                    alpha_per_trade=280.0,
                    profit_factor=3.9
                ),
                Wallet(
                    address="0x614dc8d37a5be5530df5eb42bf0082b43b679b84",
                    status="active",
                    tier="standard",
                    all_time_pnl_usd=142000.0,
                    win_rate_pct=76.4,
                    baleen_score=86.0,
                    ai_style_tag="Volume Whale",
                    ai_summary="Titan VIP: mr.ozi - Consistent high-volume probability trader.",
                    avg_trades_per_day=7.2,
                    trades_per_hour=0.9,
                    wilson_lb=71.0,
                    alpha_per_trade=150.0,
                    profit_factor=2.8
                ),
                Wallet(
                    address="0x7f9e2d1dd239272365e648434688970979a40879",
                    status="active",
                    tier="standard",
                    all_time_pnl_usd=115000.0,
                    win_rate_pct=74.8,
                    baleen_score=84.0,
                    ai_style_tag="Swing Whale",
                    ai_summary="Titan VIP: nojnn - Systematic swing trader across competitive binary contracts.",
                    avg_trades_per_day=4.9,
                    trades_per_hour=0.6,
                    wilson_lb=69.0,
                    alpha_per_trade=130.0,
                    profit_factor=2.5
                ),
            ]
            db.add_all(vip_wallets)
            await db.commit()
            logger.info("Auto-seeded 6 VIP Alpha Whales on startup.")
    
    # Schedule workers (Discovery runs every 20 minutes for continuous whale pipeline growth)
    scheduler.add_job(run_discovery, 'interval', minutes=20, id='discovery_job')
    
    # Rescoring runs every 24 hours
    async def nightly_job():
        await run_rescoring()
        await run_analysis()
        
    scheduler.add_job(nightly_job, 'interval', hours=24, id='nightly_job')
    scheduler.add_job(keep_alive_job, 'interval', minutes=5, id='keep_alive_job')
    scheduler.start()
    logger.info("Scheduler started with 5-minute keep-alive ping cadence.")
    
    # Fire initial ping in background
    asyncio.create_task(keep_alive_job())
    
    # Start live Polymarket trade mirror for active basket
    from app.services.live_poller import live_trade_mirror
    asyncio.create_task(live_trade_mirror.start())
    logger.info("Live Polymarket trade mirror initialized.")

    # Start Mark-to-Market live valuation & consensus service
    from app.services.mark_to_market import mark_to_market_service
    asyncio.create_task(mark_to_market_service.start())
    logger.info("Mark-to-Market Valuation & Consensus Service initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    from app.services.live_poller import live_trade_mirror
    from app.services.mark_to_market import mark_to_market_service
    await live_trade_mirror.stop()
    await mark_to_market_service.stop()
    scheduler.shutdown()

@app.get("/health")
async def health_check():
    global last_cron_ping_time
    last_cron_ping_time = time.time()
    return {
        "status": "ok",
        "service": "Baleen Backend",
        "uptime_seconds": round(time.time() - server_start_time, 1),
        "last_ping": last_cron_ping_time
    }

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
    return {"status": "ok", "service": "Baleen Backend", "message": "Welcome to Baleen API"}
