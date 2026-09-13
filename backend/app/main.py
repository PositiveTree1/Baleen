import asyncio
import logging
import os
import time
import httpx
from datetime import datetime
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.config import settings
from app.database import init_db, get_db
from app.auth import require_admin
from app.models import User
from app.services import paper_runs  # Register default operational run isolation.
from app.api import wallets, execution_logs, users, admin, signals, events, copilot, live_trading
from app.api import live_setup
from app.workers.discovery_worker import run_discovery
from app.workers.scoring_worker import run_rescoring
from app.workers.analysis_worker import run_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Baleen Backend", version="0.1.0")
app.include_router(live_setup.router)

# Enable Gzip compression (compresses responses > 500 bytes by ~85%)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Explicit CORS configuration (no wildcard credentials)
cors_env = os.environ.get("CORS_ALLOWED_ORIGINS")
if cors_env:
    allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://baleen.ai",
    ]
    frontend_url = os.environ.get("FRONTEND_URL") or os.environ.get("VERCEL_URL")
    if frontend_url:
        if not frontend_url.startswith("http"):
            frontend_url = f"https://{frontend_url}"
        allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*(\.vercel\.app|\.up\.railway\.app|\.railway\.app)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wallets.router)
app.include_router(execution_logs.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(signals.router)
app.include_router(events.router)
app.include_router(copilot.router)
app.include_router(live_trading.router)

scheduler = AsyncIOScheduler()

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

async def _auto_discovery_if_empty():
    """Check if the active basket has fewer than 30 qualified wallets (Top 10 + 20 bench)
    and auto-trigger discovery with curated priority seeds if needed.
    """
    from app.database import SessionLocal
    from app.models import Wallet
    try:
        async with SessionLocal() as db:
            active_count = (await db.execute(
                select(func.count()).select_from(Wallet).where(Wallet.status == "active")
            )).scalar() or 0
            
            if active_count < 30:
                logger.info(
                    f"🔍 Active basket has {active_count}/30 required whales (Top 10 + 20 bench). "
                    "Auto-triggering discovery scan with curated priority seeds..."
                )
                await asyncio.sleep(4)
                await run_discovery()
                logger.info("✅ Auto-discovery completed.")
            else:
                logger.info(f"Database has {active_count} active qualified wallets. Skipping auto-discovery.")
    except Exception as e:
        logger.error(f"Auto-discovery check failed: {e}")

@app.on_event("startup")
async def startup_event():
    # Init DB
    await init_db()
    
    if os.environ.get("TESTING") == "1" or not settings.RUN_BACKGROUND_WORKERS:
        logger.info("Background scheduler and poller are disabled for this API process.")
        return

    # Restore last discovery state from DB (survives restarts)
    from app.discovery.scanner import load_discovery_state_from_db
    await load_discovery_state_from_db()
    
    # Log database type prominently
    from app.database import _using_sqlite_fallback, engine
    db_type = "SQLite (LOCAL FALLBACK)" if _using_sqlite_fallback else f"PostgreSQL ({engine.url.drivername})"
    logger.info(f"{'⚠️' if _using_sqlite_fallback else '✅'} Active database: {db_type}")
    
    # Schedule workers (Discovery runs every 20 minutes for continuous whale pipeline growth)
    scheduler.add_job(run_discovery, 'interval', minutes=20, id='discovery_job')
    
    # Rescoring runs every 24 hours
    async def nightly_job():
        await run_rescoring()
        await run_analysis()
        
    scheduler.add_job(nightly_job, 'interval', hours=24, id='nightly_job')
    scheduler.add_job(keep_alive_job, 'interval', minutes=5, id='keep_alive_job')
    from app.services.signal_worker import drain_signal_inbox
    scheduler.add_job(drain_signal_inbox, 'interval', seconds=5, id='signal_inbox_job', max_instances=1)
    from app.services.live_reconciliation_worker import reconcile_live_accounts
    scheduler.add_job(reconcile_live_accounts, 'interval', seconds=10, id='live_reconciliation_job', max_instances=1)
    from app.services.live_copy_worker import run_live_copy
    scheduler.add_job(run_live_copy, 'interval', seconds=3, id='live_copy_job', max_instances=1)
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

    # Start automated periodic disk backup service
    from app.services.disk_backup import disk_backup_service
    asyncio.create_task(disk_backup_service.start())
    logger.info("Disk Backup Service initialized.")

    # Auto-trigger discovery if the database is empty (e.g. fresh deploy)
    asyncio.create_task(_auto_discovery_if_empty())

    # Auto-synchronize thresholds and rescore active basket on startup
    from app.scoring.basket import refresh_basket
    from app.database import SessionLocal
    async def _auto_rescore_startup():
        await asyncio.sleep(3)
        try:
            async with SessionLocal() as db:
                await refresh_basket(db)
                logger.info("✅ Automatic startup basket rescore and threshold synchronization complete.")
        except Exception as e:
            logger.warning(f"Startup basket rescore note: {e}")

    asyncio.create_task(_auto_rescore_startup())

@app.on_event("shutdown")
async def shutdown_event():
    from app.services.live_poller import live_trade_mirror
    from app.services.mark_to_market import mark_to_market_service
    from app.services.disk_backup import disk_backup_service
    await live_trade_mirror.stop()
    await mark_to_market_service.stop()
    await disk_backup_service.stop()
    scheduler.shutdown()

@app.get("/health")
async def health_check():
    """Liveness probe: verifies the process is running."""
    global last_cron_ping_time
    from app.database import _using_sqlite_fallback
    last_cron_ping_time = time.time()
    return {
        "status": "ok",
        "service": "Baleen Backend",
        "uptime_seconds": round(time.time() - server_start_time, 1),
        "last_ping": last_cron_ping_time,
        "database": "PostgreSQL" if not _using_sqlite_fallback else "SQLite (DEGRADED)",
    }

@app.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe: verifies database connectivity, schema migration completeness, production requirements, and listener status.
    Returns 503 if dependencies are unreachable or invalid.
    """
    from app.database import _using_sqlite_fallback, is_production_environment
    from app.api.admin import last_listener_heartbeat
    from app.migrations import check_schema_completeness, LATEST_SCHEMA_VERSION

    # 1. Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness check failed: database unreachable: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": "Database connectivity check failed"}
        )

    # 2. Check schema migration completeness
    try:
        conn = await db.connection()
        is_complete, cur_ver, detail = await check_schema_completeness(conn)
        if not is_complete:
            logger.warning(f"Readiness check failed: {detail}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "error": detail,
                    "current_schema_version": cur_ver,
                    "required_schema_version": LATEST_SCHEMA_VERSION
                }
            )
    except Exception as e:
        logger.error(f"Readiness check failed on schema completeness verification: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": f"Schema verification error: {e}"}
        )

    # 3. Reject SQLite in production deployments
    if is_production_environment() and _using_sqlite_fallback:
        logger.critical("Readiness check failed: PostgreSQL required in production but SQLite is active.")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": "PostgreSQL required in production environment"}
        )

    # 4. Dynamic listener status
    now = time.time()
    if last_listener_heartbeat == 0.0:
        listener_status = "UNKNOWN"
    elif (now - last_listener_heartbeat) < 60:
        listener_status = "ONLINE"
    else:
        listener_status = "OFFLINE"

    return {
        "status": "ready",
        "service": "Baleen Backend",
        "database": "PostgreSQL" if not _using_sqlite_fallback else "SQLite",
        "schema_version": cur_ver,
        "listener": listener_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    from app.models import Wallet, ExecutionLog
    from app.api.admin import last_listener_heartbeat
    
    wallet_count = (await db.execute(
        select(func.count()).select_from(Wallet).where(Wallet.status == "active")
    )).scalar() or 0
    
    total_volume = (await db.execute(
        select(func.coalesce(func.sum(ExecutionLog.notional_usd), 0))
    )).scalar() or 0

    now = time.time()
    if last_listener_heartbeat == 0.0:
        indexer_status = "UNKNOWN"
    elif (now - last_listener_heartbeat) < 60:
        indexer_status = "ONLINE"
    else:
        indexer_status = "OFFLINE"
    
    return {
        "totalVolumeMirrored": round(total_volume, 2),
        "activeBasketWhales": wallet_count,
        "indexerStatus": indexer_status
    }

@app.get("/api/diagnostics")
async def diagnostics(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Test all external API connections and report results. Requires administrator privileges."""
    from app.models import Wallet, User
    from app.database import _using_sqlite_fallback, engine
    results = {}
    
    # Test Polymarket Data API
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in [
            ("polymarket_leaderboard", "https://data-api.polymarket.com/v1/leaderboard"),
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
        results["database"] = {
            "status": "OK",
            "type": "Supabase PostgreSQL" if not _using_sqlite_fallback else "SQLite (Local Fallback)",
            "driver": engine.url.drivername,
            "wallets": wallet_count,
            "users": user_count,
        }
    except Exception as e:
        results["database"] = {"status": "ERROR", "error": str(e)[:200]}
    
    # Test scheduler
    jobs = [{"id": job.id, "next_run": str(job.next_run_time)} for job in scheduler.get_jobs()]
    results["scheduler"] = {"jobs": jobs}
    
    return results

@app.get("/")
async def root():
    return {"status": "ok", "service": "Baleen Backend", "message": "Welcome to Baleen API"}
