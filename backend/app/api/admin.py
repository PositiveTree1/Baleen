import asyncio
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Wallet, User, ExecutionLog
from datetime import datetime
import time

router = APIRouter(prefix="/api/admin", tags=["admin"])

last_listener_heartbeat = 0.0

@router.post("/heartbeat")
async def listener_heartbeat(payload: dict = Body(...)):
    global last_listener_heartbeat
    last_listener_heartbeat = time.time()
    return {"status": "ok", "received_at": last_listener_heartbeat}

@router.post("/trigger-discovery")
async def trigger_discovery():
    from app.workers.discovery_worker import run_discovery
    asyncio.create_task(run_discovery())
    return {"status": "triggered", "message": "Discovery worker started in background."}

@router.get("/status")
async def get_admin_status(db: AsyncSession = Depends(get_db)):
    """Returns real-time progress, server health, and database metrics in a unified response."""
    from app.discovery.scanner import discovery_state
    from app.main import server_start_time, last_cron_ping_time
    from app.database import _using_sqlite_fallback, engine
    
    # DB stats
    total_wallets = (await db.execute(select(func.count()).select_from(Wallet))).scalar() or 0
    pending_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'pending'))).scalar() or 0
    active_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'active'))).scalar() or 0
    rejected_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'rejected'))).scalar() or 0
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    trade_count = (await db.execute(select(func.count()).select_from(ExecutionLog))).scalar() or 0

    # Listener is online if heartbeat in last 60s or if started recently
    listener_online = (time.time() - last_listener_heartbeat) < 60 if last_listener_heartbeat > 0 else True

    # Database type reporting
    db_driver = engine.url.drivername
    is_postgres = "postgres" in db_driver
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - server_start_time,
        "last_cron_ping": last_cron_ping_time,
        "discovery_state": discovery_state,
        "db_stats": {
            "total": total_wallets,
            "pending": pending_wallets,
            "active": active_wallets,
            "rejected": rejected_wallets
        },
        "database": {
            "type": "Supabase PostgreSQL" if is_postgres else "SQLite (Local Failover)",
            "using_sqlite_fallback": _using_sqlite_fallback,
            "totalWallets": total_wallets,
            "activeWallets": active_wallets,
            "pendingWallets": pending_wallets,
            "rejectedWallets": rejected_wallets,
            "totalUsers": user_count,
            "totalTrades": trade_count,
        },
        "jobs": {
            "discoveryInterval": "20m",
            "scoringInterval": "24h",
            "analysisInterval": "24h",
        },
        "services": {
            "backend": "ONLINE",
            "database": "ONLINE" if not _using_sqlite_fallback else "DEGRADED (SQLite fallback)",
            "listener": "ONLINE" if listener_online else "OFFLINE",
        }
    }

@router.get("/discovery-progress")
async def get_discovery_progress():
    """Returns real-time progress of Polymarket scraping & scoring pipeline."""
    from app.discovery.scanner import discovery_state
    return discovery_state

@router.post("/re-evaluate")
async def re_evaluate_wallets(db: AsyncSession = Depends(get_db)):
    """
    Clears stale test data and completely re-evaluates all candidates
    directly from live Polymarket API using Titan Engine algorithms.
    """
    from app.discovery.scanner import scan_for_wallets
    count = await scan_for_wallets(db, full_refresh=True)
    
    active_count = (await db.execute(
        select(func.count()).select_from(Wallet).where(
            Wallet.status == "active",
            Wallet.is_hft == False,
            Wallet.dormant == False
        )
    )).scalar() or 0
    
    return {
        "status": "completed",
        "evaluated": count,
        "active": active_count,
        "message": f"Successfully re-evaluated {count} wallets from Polymarket. {active_count} active in basket."
    }

@router.post("/purge-and-rescan")
async def purge_and_rescan(db: AsyncSession = Depends(get_db)):
    """
    Hard-wipes all existing wallets and starts background discovery from scratch from Polymarket API.
    """
    from app.discovery.scanner import scan_for_wallets, discovery_state
    
    if discovery_state["status"] == "running":
        return {"status": "running", "message": "Discovery already in progress."}
        
    async def _run_bg():
        from app.database import SessionLocal
        async with SessionLocal() as bg_db:
            await scan_for_wallets(bg_db, full_refresh=True)
            
    asyncio.create_task(_run_bg())
    return {
        "status": "started",
        "message": "Database purge initiated. Background Polymarket scraping & audit started."
    }

@router.get("/wallets")
async def get_all_wallets(
    status: str = None,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Wallet)
    if status:
        stmt = stmt.where(Wallet.status == status.lower())
    stmt = stmt.order_by(Wallet.all_time_pnl_usd.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    wallets = result.scalars().all()
    return [{
        "address": w.address,
        "status": w.status,
        "tier": w.tier,
        "baleenScore": w.baleen_score or 0,
        "winRatePct": w.win_rate_pct or 0,
        "allTimePnlUsd": w.all_time_pnl_usd or 0,
        "avgTradesPerDay": w.avg_trades_per_day or 0,
        "totalTradesAnalyzed": w.total_trades_analyzed or 0,
        "maxDrawdownPct": w.max_drawdown_pct or 0,
        "rejectionReason": w.rejection_reason,
        "aiSummary": w.ai_summary,
        "aiStyleTag": w.ai_style_tag,
        "dormant": w.dormant,
        "firstSeenAt": w.first_seen_at.isoformat() if w.first_seen_at else None,
        "lastScoredAt": w.last_scored_at.isoformat() if w.last_scored_at else None,
    } for w in wallets]
