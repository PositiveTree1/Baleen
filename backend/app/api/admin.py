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
        
    # Execute full hard wipe of EVERYTHING
    await hard_wipe_all_database(db)
        
    async def _run_bg():
        from app.database import SessionLocal
        async with SessionLocal() as bg_db:
            await scan_for_wallets(bg_db, full_refresh=True)
            
    asyncio.create_task(_run_bg())
    return {
        "status": "started",
        "message": "Complete database wipe successful. Background Polymarket scraping & audit started."
    }

@router.post("/hard-wipe-all")
async def hard_wipe_all_database(db: AsyncSession = Depends(get_db)):
    """
    Completely wipes ALL database tables:
    - Execution logs
    - Portfolio snapshots
    - Wallet snapshots
    - Wallets (all whale records)
    - Fee charges
    - KV store
    - Resets all users to $10,000.00
    - Resets discovery state to idle
    """
    from app.models import ExecutionLog, PortfolioSnapshot, WalletSnapshot, Wallet, FeeCharge, KeyValue, User
    from sqlalchemy import delete
    from app.discovery.scanner import discovery_state
    from datetime import datetime

    # 1. Delete all transactional, historical & whale tables
    await db.execute(delete(ExecutionLog))
    await db.execute(delete(PortfolioSnapshot))
    await db.execute(delete(WalletSnapshot))
    await db.execute(delete(Wallet))
    await db.execute(delete(FeeCharge))
    await db.execute(delete(KeyValue))

    # 2. Reset user balances to clean $10k
    now_dt = datetime.utcnow()
    stmt_users = select(User)
    users = (await db.execute(stmt_users)).scalars().all()
    for u in users:
        u.sandbox_balance_usd = 10000.0
        u.sandbox_starting_balance_usd = 10000.0
        u.sandbox_high_water_mark_usd = 10000.0
        db.add(PortfolioSnapshot(
            user_id=u.id,
            timestamp=now_dt,
            balance=10000.0,
            total_pnl=0.0,
            active_trades_count=0
        ))

    # 3. Add global baseline snapshot
    db.add(PortfolioSnapshot(
        user_id=None,
        timestamp=now_dt,
        balance=10000.0,
        total_pnl=0.0,
        active_trades_count=0
    ))

    await db.commit()

    # 4. Reset discovery in-memory state
    discovery_state.update({
        "status": "idle",
        "progress_pct": 0,
        "step_description": "Database completely wiped. Clean state initialized.",
        "wallets_scanned": 0,
        "active_whales_in_basket": 0,
        "gold_snipers": 0,
        "started_at": None,
        "error_message": None
    })

    return {
        "status": "success",
        "message": "Complete factory reset successful. All database tables and state wiped."
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

@router.get("/export-trades-csv")
async def export_trades_csv(db: AsyncSession = Depends(get_db)):
    """Exports all trade execution logs as RFC-compliant CSV string."""
    import io, csv
    from app.models import ExecutionLog, Wallet
    from app.services.mark_to_market import get_live_price
    from fastapi.responses import PlainTextResponse

    stmt = select(ExecutionLog).order_by(ExecutionLog.executed_at.desc())
    logs = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Execution ID", "Timestamp UTC", "Source Whale Address", "Market Title", 
        "Condition ID", "Side", "Outcome", "Fill Price USD", "Live MTM Price USD", 
        "Notional USD", "Polymarket Fee USD", "Net PnL USD", "PnL %", "Status", "Tx Hash"
    ])

    for l in logs:
        fill_p = float(l.user_fill_price or l.whale_entry_price or 0.5)
        cur_p = get_live_price(l.market_condition_id or "", outcome=l.resolution_outcome or "Yes", asset=l.onchain_tx_hash or "", fallback=fill_p)
        fee = float(l.fee_usd or 0.0)
        notional = float(l.notional_usd or 0.0)
        
        if l.realized_pnl_usd is not None:
            net_p = float(l.realized_pnl_usd)
        elif fill_p > 0:
            gross = notional * ((cur_p - fill_p) / fill_p) if l.side == "BUY" else notional * ((fill_p - cur_p) / fill_p)
            net_p = gross - fee
        else:
            net_p = 0.0
            
        pnl_pct = (net_p / notional * 100.0) if notional > 0 else 0.0
        
        writer.writerow([
            str(l.id),
            l.executed_at.isoformat() if l.executed_at else "",
            l.source_wallet_address,
            l.market_question,
            l.market_condition_id,
            l.side,
            l.resolution_outcome or "Yes",
            f"{fill_p:.4f}",
            f"{cur_p:.4f}",
            f"{notional:.2f}",
            f"{fee:.4f}",
            f"{net_p:.2f}",
            f"{pnl_pct:.2f}%",
            l.status,
            l.onchain_tx_hash or ""
        ])

    csv_content = output.getvalue()
    return PlainTextResponse(content=csv_content, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=baleen_all_trades_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    })

@router.post("/analyze-portfolio-ai")
async def analyze_portfolio_ai(db: AsyncSession = Depends(get_db)):
    """Runs a full quantitative AI attribution analysis across all historical and active copy trades."""
    from app.models import ExecutionLog, Wallet
    from app.services.mark_to_market import get_live_price
    from app.analysis.ai_summary import get_groq_client

    stmt = select(ExecutionLog).where(ExecutionLog.status == "FILLED").order_by(ExecutionLog.executed_at.desc())
    logs = (await db.execute(stmt)).scalars().all()

    if not logs:
        return {
            "status": "empty",
            "summary": "No active or historical fills recorded to evaluate.",
            "metrics": {},
            "recommendations": []
        }

    total_trades = len(logs)
    whale_stats: dict[str, dict] = {}
    total_volume = 0.0
    total_net_pnl = 0.0
    total_fees = 0.0
    wins = 0
    losses = 0

    for l in logs:
        addr = l.source_wallet_address.lower()
        if addr not in whale_stats:
            whale_stats[addr] = {"trades": 0, "volume": 0.0, "net_pnl": 0.0, "wins": 0, "losses": 0}
            
        fill_p = float(l.user_fill_price or l.whale_entry_price or 0.5)
        cur_p = get_live_price(l.market_condition_id or "", outcome=l.resolution_outcome or "Yes", asset=l.onchain_tx_hash or "", fallback=fill_p)
        notional = float(l.notional_usd or 0.0)
        fee = float(l.fee_usd or 0.0)
        
        gross = (notional * ((cur_p - fill_p) / fill_p)) if l.side == "BUY" else (notional * ((fill_p - cur_p) / fill_p))
        net_p = l.realized_pnl_usd if l.realized_pnl_usd is not None else (gross - fee)
        
        total_volume += notional
        total_net_pnl += net_p
        total_fees += fee
        
        whale_stats[addr]["trades"] += 1
        whale_stats[addr]["volume"] += notional
        whale_stats[addr]["net_pnl"] += net_p
        
        if net_p >= 0:
            wins += 1
            whale_stats[addr]["wins"] += 1
        else:
            losses += 1
            whale_stats[addr]["losses"] += 1

    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    
    # Sort top alpha vs drag whales
    sorted_whales = sorted(whale_stats.items(), key=lambda x: x[1]["net_pnl"], reverse=True)
    top_alpha_whales = [{"address": w[0], "pnl": round(w[1]["net_pnl"], 2), "win_rate": round(w[1]["wins"]/w[1]["trades"]*100, 1)} for w in sorted_whales[:3]]
    drag_whales = [{"address": w[0], "pnl": round(w[1]["net_pnl"], 2), "win_rate": round(w[1]["wins"]/w[1]["trades"]*100, 1)} for w in sorted_whales[-3:] if w[1]["net_pnl"] < 0]

    # Generate AI executive synthesis
    client = get_groq_client()
    ai_synthesis = f"Audited {total_trades} trade fills across {len(whale_stats)} active whales. Aggregate portfolio generated ${total_net_pnl:+,.2f} net PnL ({win_rate:.1f}% win rate) on ${total_volume:,.2f} gross volume with ${total_fees:,.2f} quadratic fees."
    
    if client:
        try:
            prompt = f"""
            You are a senior quantitative risk manager at a prediction market copy-trading fund.
            Audit these live portfolio execution stats:
            - Total Fills: {total_trades}
            - Net P&L: ${total_net_pnl:,.2f}
            - Win Rate: {win_rate:.1f}%
            - Total Volume: ${total_volume:,.2f}
            - Total Fees: ${total_fees:,.2f}
            - Top Alpha Generating Wallets: {top_alpha_whales}
            - Drag / Underperforming Wallets: {drag_whales}
            
            Provide:
            1. A 2-sentence executive summary of portfolio health, slippage drag, and alpha sources.
            2. Three specific, actionable suggestions (e.g. adjust sizing on top snipers, demote drag wallets).
            """
            resp = await client.chat.completions.create(
                model="groq/compound-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2
            )
            ai_synthesis = resp.choices[0].message.content or ai_synthesis
        except Exception:
            pass

    return {
        "status": "success",
        "total_trades": total_trades,
        "total_volume": round(total_volume, 2),
        "net_pnl": round(total_net_pnl, 2),
        "win_rate": round(win_rate, 1),
        "total_fees": round(total_fees, 2),
        "top_alpha_whales": top_alpha_whales,
        "drag_whales": drag_whales,
        "ai_report": ai_synthesis
    }
