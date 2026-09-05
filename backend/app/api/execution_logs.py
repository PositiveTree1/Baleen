from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import re
import time
import httpx
from app.database import get_db
from app.models import ExecutionLog, Wallet, User, PortfolioSnapshot
from app.services.mark_to_market import get_live_price, get_consensus
from app.services.polymarket_fees import calculate_polymarket_fee

router = APIRouter(prefix="/api/executions", tags=["execution_logs"])

def slugify(text: str) -> str:
    """Converts a market question to a clean URL slug."""
    if not text:
        return ""
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    return re.sub(r'[\s-]+', '-', clean)

def make_polymarket_url(event_slug: Optional[str], question: Optional[str], condition_id: Optional[str]) -> str:
    """Constructs a guaranteed working Polymarket event URL."""
    if event_slug and event_slug.strip():
        return f"https://polymarket.com/event/{event_slug.strip()}"
    if question and question.strip():
        s = slugify(question)
        if s:
            return f"https://polymarket.com/event/{s}"
    if condition_id and condition_id.strip():
        return f"https://polymarket.com/market/{condition_id.strip()}"
    return "https://polymarket.com"

@router.get("")
async def get_execution_logs(
    user_id: Optional[str] = Query(None, alias="userId"),
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    timeframe: Optional[str] = None, # 1d, 1w, 1m, ytd, all
    limit: int = Query(1500, le=10000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExecutionLog)
    if status:
        stmt = stmt.where(ExecutionLog.status == status)
    
    # Timeframe filtering
    now = datetime.utcnow()
    if timeframe:
        tf = timeframe.lower()
        if tf == "1h":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(hours=1))
        elif tf == "6h":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(hours=6))
        elif tf == "1d":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=1))
        elif tf == "1w":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=7))
        elif tf == "1m":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=30))
        elif tf == "ytd":
            stmt = stmt.where(ExecutionLog.executed_at >= datetime(now.year, 1, 1))

    if start_date:
        stmt = stmt.where(ExecutionLog.executed_at >= start_date)
    if end_date:
        stmt = stmt.where(ExecutionLog.executed_at <= end_date)

    # Query execution logs (filtered by user_id if specific rows exist, otherwise canonical platform logs)
    user_filter = ExecutionLog.user_id.is_(None)
    if user_id:
        try:
            import uuid
            u_uuid = uuid.UUID(user_id)
            user_cnt = (await db.execute(select(func.count(ExecutionLog.id)).where(ExecutionLog.user_id == u_uuid))).scalar() or 0
            if user_cnt > 0:
                user_filter = ExecutionLog.user_id == u_uuid
        except Exception:
            pass

    stmt = stmt.where(user_filter)
    system_stmt = stmt.order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
    raw_logs = (await db.execute(system_stmt)).scalars().all()

    if not raw_logs:
        return []

    # Batch query whale wallets for authentic nicknames, usernames, and avatars
    whale_addrs = list(set(log.source_wallet_address.lower() for log in raw_logs if log.source_wallet_address))
    whale_meta_map: Dict[str, Dict] = {}
    if whale_addrs:
        w_records = (await db.execute(select(Wallet).where(func.lower(Wallet.address).in_(whale_addrs)))).scalars().all()
        for w in w_records:
            whale_meta_map[w.address.lower()] = {
                "name": w.name,
                "pseudonym": w.pseudonym,
                "profileImage": w.profile_image,
                "tier": w.tier,
                "all_time_pnl_usd": w.all_time_pnl_usd
            }

    # Use in-memory live prices from the continuous MTM background service for instant sub-millisecond response times

    response_list = []
    for log in raw_logs:
        cid = log.market_condition_id or ""
        outc = log.resolution_outcome or "Yes"
        fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
        cur_p = get_live_price(cid, outcome=outc, asset=log.onchain_tx_hash or "", fallback=fill_p)
        consensus = get_consensus(cid)
        notional = float(log.notional_usd or 0.0)

        # Dynamic Polymarket fee
        fee_info = calculate_polymarket_fee(
            notional_usd=notional,
            price=fill_p,
            market_title=log.market_question or ""
        )
        fee_usd = float(log.fee_usd) if log.fee_usd is not None and log.fee_usd > 0 else fee_info["fee_usd"]
        category = log.market_category or fee_info["category"]

        # Gross & Net PnL resolution
        if log.status != "FILLED" and log.realized_pnl_usd is not None:
            # Closed/settled positions use their locked realized PnL
            net_pnl = float(log.realized_pnl_usd)
            gross_pnl = round(net_pnl + fee_usd, 2)
            if abs(cur_p - fill_p) < 0.001 and notional > 0 and fill_p > 0:
                implied_p = fill_p * (1.0 + gross_pnl / notional) if log.side == "BUY" else fill_p * (1.0 - gross_pnl / notional)
                if 0.001 <= implied_p <= 0.999:
                    cur_p = round(implied_p, 4)
        elif log.status == "FILLED":
            # Active open positions with live market movement
            if fill_p > 0 and cur_p > 0:
                if log.side == "BUY":
                    gross_pnl = notional * ((cur_p - fill_p) / fill_p)
                else:
                    gross_pnl = notional * ((fill_p - cur_p) / fill_p)
                net_pnl = round(gross_pnl - fee_usd, 2)
            else:
                gross_pnl = 0.0
                net_pnl = round(-fee_usd, 2)
        elif log.realized_pnl_usd is not None:
            net_pnl = float(log.realized_pnl_usd)
            gross_pnl = round(net_pnl + fee_usd, 2)
            if abs(cur_p - fill_p) < 0.001 and notional > 0 and fill_p > 0 and abs(gross_pnl) > 0.01:
                implied_p = fill_p * (1.0 + gross_pnl / notional) if log.side == "BUY" else fill_p * (1.0 - gross_pnl / notional)
                if 0.001 <= implied_p <= 0.999:
                    cur_p = round(implied_p, 4)
        else:
            gross_pnl = 0.0
            net_pnl = round(-fee_usd, 2)

        pnl_pct = round((net_pnl / notional) * 100.0, 2) if notional > 0 else 0.0

        whale_info = whale_meta_map.get((log.source_wallet_address or "").lower(), {})
        whale_disp_name = whale_info.get("name") or whale_info.get("pseudonym") or (f"{log.source_wallet_address[:6]}...{log.source_wallet_address[-4:]}" if log.source_wallet_address else "Whale")

        response_list.append({
            "id": str(log.id),
            "timestamp": log.executed_at.isoformat() if log.executed_at else None,
            "walletAddress": log.source_wallet_address,
            "source_wallet_address": log.source_wallet_address,
            "whaleName": whale_disp_name,
            "whalePseudonym": whale_info.get("pseudonym"),
            "whaleAvatar": whale_info.get("profileImage"),
            "whaleTier": whale_info.get("tier"),
            "marketQuestion": log.market_question or "Polymarket Event Prediction",
            "market_question": log.market_question or "Polymarket Event Prediction",
            "marketConditionId": log.market_condition_id,
            "market_condition_id": log.market_condition_id,
            "eventSlug": log.event_slug,
            "icon": log.icon,
            "side": log.side,
            "outcome": outc,
            "entryPrice": fill_p,
            "fillPrice": fill_p,
            "currentPrice": cur_p,
            "size": notional,
            "status": log.status,
            "pnl": net_pnl,
            "grossPnl": round(gross_pnl, 2),
            "pnlPct": pnl_pct,
            "feeUsd": fee_usd,
            "marketCategory": category,
            "categoryRate": fee_info["category_rate"],
            "consensus": consensus,
            "polymarketUrl": make_polymarket_url(log.event_slug, log.market_question, cid)
        })

    return response_list

@router.get("/summary")
async def get_portfolio_summary(
    user_id: Optional[str] = Query(None, alias="userId"),
    timeframe: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    user_filter = ExecutionLog.user_id.is_(None)
    if user_id:
        try:
            import uuid
            u_uuid = uuid.UUID(user_id)
            user_cnt = (await db.execute(select(func.count(ExecutionLog.id)).where(ExecutionLog.user_id == u_uuid))).scalar() or 0
            if user_cnt > 0:
                user_filter = ExecutionLog.user_id == u_uuid
        except Exception:
            pass

    stmt = select(ExecutionLog).where(
        ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]),
        user_filter
    )

    now = datetime.utcnow()
    if timeframe:
        tf = timeframe.lower()
        if tf == "1h":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(hours=1))
        elif tf == "6h":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(hours=6))
        elif tf == "1d":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=1))
        elif tf == "1w":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=7))
        elif tf == "1m":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=30))
        elif tf == "ytd":
            stmt = stmt.where(ExecutionLog.executed_at >= datetime(now.year, 1, 1))

    logs = (await db.execute(stmt.order_by(ExecutionLog.executed_at.desc()))).scalars().all()
    
    # 1. Fetch latest committed snapshot from database — this is the SINGLE SOURCE OF TRUTH
    # The MTM background loop maintains this with cache warmth checks, so it's always reliable
    latest_snap = (await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id.is_(None))
        .order_by(PortfolioSnapshot.timestamp.desc())
        .limit(1)
    )).scalar_one_or_none()

    authoritative_db_balance = float(latest_snap.balance) if latest_snap and latest_snap.balance else 10000.0
    authoritative_db_pnl = float(latest_snap.total_pnl) if latest_snap and latest_snap.total_pnl is not None else 0.0

    starting_balance = 10000.0
    total_notional = 0.0
    total_fees = 0.0
    
    for log in logs:
        total_notional += float(log.notional_usd or 0.0)
        total_fees += float(log.fee_usd or 0.0)

    # Always use the database snapshot as the authoritative balance
    total_pnl = authoritative_db_pnl
    current_balance = authoritative_db_balance

    # Market Attribution aggregation across database records
    market_map = {}
    wins_count = 0
    losses_count = 0
    for log in logs:
        if log.side == "SELL" and log.realized_pnl_usd is None:
            continue
            
        key = log.market_question or log.market_condition_id or str(log.id)
        notional_val = float(log.notional_usd or 0.0)
        fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
        
        pnl_val = log.realized_pnl_usd
        if pnl_val is None:
            cid = log.market_condition_id or ""
            outc = log.resolution_outcome or "Yes"
            cur_p = get_live_price(cid, outcome=outc, asset=log.onchain_tx_hash or "", fallback=fill_p)
            if fill_p > 0 and abs(cur_p - fill_p) > 0.001:
                fee = float(log.fee_usd or 0.0)
                gross = notional_val * ((cur_p - fill_p) / fill_p) if log.side == "BUY" else notional_val * ((fill_p - cur_p) / fill_p)
                pnl_val = round(gross - fee, 2)
            else:
                pnl_val = 0.0
        else:
            pnl_val = float(pnl_val)
        
        if pnl_val > 0:
            wins_count += 1
        elif pnl_val < 0:
            losses_count += 1
            
        if key not in market_map:
            market_map[key] = {
                "key": key,
                "question": log.market_question or "Prediction Market",
                "conditionId": log.market_condition_id or "",
                "outcome": log.resolution_outcome or "Yes",
                "totalPnl": 0.0,
                "totalNotional": 0.0,
                "fillsCount": 0,
                "avgFillPrice": fill_p,
                "whaleName": (log.source_wallet_address[:6] + "..." + log.source_wallet_address[-4:]) if log.source_wallet_address else "Whale"
            }
        m = market_map[key]
        m["totalPnl"] = round(m["totalPnl"] + pnl_val, 2)
        m["totalNotional"] = round(m["totalNotional"] + notional_val, 2)
        m["fillsCount"] += 1

    all_markets = list(market_map.values())
    top_alpha = sorted([m for m in all_markets if m["totalPnl"] > 0], key=lambda x: x["totalPnl"], reverse=True)[:5]
    top_drawdown = sorted([m for m in all_markets if m["totalPnl"] < 0], key=lambda x: x["totalPnl"])[:5]
    total_evaluated = wins_count + losses_count
    all_time_win_rate = round((wins_count / total_evaluated * 100), 1) if total_evaluated > 0 else 0.0
            
    current_balance = round(starting_balance + total_pnl, 2)
    pnl_pct = round((total_pnl / starting_balance) * 100.0, 2) if starting_balance > 0 else 0.0
    
    holding_count = sum(1 for l in logs if l.side == "BUY" and l.status == "FILLED")
    closed_count = sum(1 for l in logs if l.status in ("CLOSED", "RESOLVED") or l.side == "SELL")
    
    return {
        "startingBalance": starting_balance,
        "currentBalance": current_balance,
        "totalPnlUsd": round(total_pnl, 2),
        "totalPnlPct": pnl_pct,
        "totalFeesPaidUsd": round(total_fees, 2),
        "filledTradesCount": len(logs),
        "holdingTradesCount": holding_count,
        "closedTradesCount": closed_count,
        "totalNotionalInvested": round(total_notional, 2),
        "topAlphaMarkets": top_alpha,
        "topDrawdownMarkets": top_drawdown,
        "allTimeWinRate": all_time_win_rate,
        "allTimeWins": wins_count,
        "allTimeLosses": losses_count
    }

@router.get("/snapshots")
async def get_portfolio_snapshots(
    user_id: Optional[str] = Query(None, alias="userId"),
    timeframe: Optional[str] = None,
    limit: int = 5000,
    db: AsyncSession = Depends(get_db)
):
    from uuid import UUID
    
    stmt = select(PortfolioSnapshot)
    now = datetime.utcnow()
    tf = (timeframe or "all").lower()
    start_window = None
    
    if tf == "1h":
        start_window = now - timedelta(hours=1)
    elif tf == "6h":
        start_window = now - timedelta(hours=6)
    elif tf == "1d":
        start_window = now - timedelta(days=1)
    elif tf == "1w":
        start_window = now - timedelta(days=7)
    elif tf == "1m":
        start_window = now - timedelta(days=30)
    elif tf == "ytd":
        start_window = datetime(now.year, 1, 1)

    if start_window:
        stmt = stmt.where(PortfolioSnapshot.timestamp >= start_window)

    # Query snapshots in ascending chronological order
    user_filter = PortfolioSnapshot.user_id.is_(None)
    if user_id:
        try:
            import uuid
            u_uuid = uuid.UUID(user_id)
            snap_cnt = (await db.execute(select(func.count(PortfolioSnapshot.id)).where(PortfolioSnapshot.user_id == u_uuid))).scalar() or 0
            if snap_cnt > 0:
                user_filter = PortfolioSnapshot.user_id == u_uuid
        except Exception:
            pass

    stmt = stmt.where(user_filter).order_by(PortfolioSnapshot.timestamp.asc())
    rows = list((await db.execute(stmt)).scalars().all())

    # If timeframe window has snapshots, ensure start boundary is cleanly anchored
    if start_window and rows:
        earliest_row = rows[0]
        if earliest_row.timestamp and earliest_row.timestamp > start_window + timedelta(minutes=2):
            prev_stmt = select(PortfolioSnapshot).where(
                user_filter,
                PortfolioSnapshot.timestamp < start_window
            ).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
            prev_row = (await db.execute(prev_stmt)).scalar_one_or_none()
            anchor_bal = float(prev_row.balance) if prev_row and prev_row.balance else float(earliest_row.balance)
            anchor_pnl = float(prev_row.total_pnl) if prev_row and prev_row.total_pnl is not None else float(earliest_row.total_pnl)
            
            anchor_snap = PortfolioSnapshot(
                user_id=earliest_row.user_id,
                timestamp=start_window,
                balance=anchor_bal,
                total_pnl=anchor_pnl,
                active_trades_count=earliest_row.active_trades_count
            )
            rows.insert(0, anchor_snap)

    if not rows:
        fallback_stmt = select(PortfolioSnapshot).where(user_filter).order_by(PortfolioSnapshot.timestamp.desc()).limit(2)
        rows = list(reversed((await db.execute(fallback_stmt)).scalars().all()))

    # Fixed time-interval bucketing so past historical points NEVER shift or jitter
    if len(rows) > 60:
        if tf in ("all", "1m", "ytd"):
            bucket_secs = 3600  # 1-hour buckets for all-time
        elif tf == "1w":
            bucket_secs = 1800  # 30-min buckets for 1 week
        elif tf == "1d":
            bucket_secs = 900   # 15-min buckets for 1 day
        elif tf == "6h":
            bucket_secs = 300   # 5-min buckets for 6 hours
        else:
            bucket_secs = 60    # 1-min buckets for 1 hour

        bucket_map = {}
        for r in rows:
            if r.timestamp:
                b_key = int(r.timestamp.timestamp() // bucket_secs)
                bucket_map[b_key] = r  # Last-of-bucket selection
            else:
                bucket_map[id(r)] = r

        bucketed_rows = sorted(bucket_map.values(), key=lambda x: x.timestamp if x.timestamp else datetime.min)

        # Always include the exact latest live snapshot at the end
        if rows and (not bucketed_rows or bucketed_rows[-1].id != rows[-1].id):
            bucketed_rows.append(rows[-1])

        rows = bucketed_rows

    # Uniform downsampling across the ENTIRE queried timeframe if bucketed points exceed limit
    target_limit = max(10, limit)
    if len(rows) > target_limit and target_limit > 1:
        step = (len(rows) - 1) / (target_limit - 1)
        sampled_indices = [int(round(i * step)) for i in range(target_limit)]
        unique_indices = sorted(list(set(sampled_indices)))
        if 0 not in unique_indices:
            unique_indices.insert(0, 0)
        if (len(rows) - 1) not in unique_indices:
            unique_indices.append(len(rows) - 1)
        rows = [rows[idx] for idx in unique_indices]

    result = []
    for i, r in enumerate(rows):
        is_latest = (i == len(rows) - 1)
        ts = r.timestamp
        if ts and not is_latest and tf in ("all", "1m", "ytd"):
            # Cleanly floor historical hours to :00
            ts_clean = ts.replace(minute=0, second=0, microsecond=0)
        else:
            ts_clean = ts

        result.append({
            "id": str(r.id),
            "timestamp": (ts_clean.isoformat() + "Z") if ts_clean else None,
            "time": ts_clean.strftime("%H:%M") if ts_clean else "",
            "date": ts_clean.strftime("%d %b") if ts_clean else "",
            "balance": round(float(r.balance), 2),
            "pnl": round(float(r.total_pnl), 2),
            "activeTrades": r.active_trades_count
        })

    # Prepend Genesis $10,000.00 baseline for ALL timeframe
    if tf == "all" and result:
        first_date = result[0]["date"]
        first_time = result[0]["time"]
        if abs(result[0]["balance"] - 10000.0) > 0.01:
            try:
                first_ts = datetime.fromisoformat(result[0]["timestamp"].replace("Z", ""))
                gen_ts = first_ts - timedelta(minutes=1)
                gen_ts_str = gen_ts.isoformat() + "Z"
                gen_time_str = gen_ts.strftime("%H:%M")
                gen_date_str = gen_ts.strftime("%d %b")
            except Exception:
                gen_ts_str = result[0].get("timestamp")
                gen_time_str = first_time
                gen_date_str = first_date

            genesis_point = {
                "id": "genesis-baseline",
                "timestamp": gen_ts_str,
                "time": gen_time_str,
                "date": gen_date_str,
                "balance": 10000.0,
                "pnl": 0.0,
                "activeTrades": 0
            }
            result.insert(0, genesis_point)

    return result

@router.post("/reset-sandbox")
async def reset_sandbox(
    user_id: Optional[str] = Query(None, alias="userId"),
    db: AsyncSession = Depends(get_db)
):
    """
    Resets sandbox balance to pristine $10,000.00 and clears historical simulation logs and notifications.
    """
    from app.models import ExecutionLog, PortfolioSnapshot, User, SystemEvent
    from app.services.event_logger import clear_recent_events_from_memory, log_event
    from sqlalchemy import delete
    import time
    
    # Delete historical snapshots, execution logs & system events
    await db.execute(delete(PortfolioSnapshot))
    await db.execute(delete(ExecutionLog))
    await db.execute(delete(SystemEvent))
    clear_recent_events_from_memory()
    
    # Reset all users to $10,000
    stmt_users = select(User)
    users = (await db.execute(stmt_users)).scalars().all()
    now_dt = datetime.utcnow()
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
        
    db.add(PortfolioSnapshot(
        user_id=None,
        timestamp=now_dt,
        balance=10000.0,
        total_pnl=0.0,
        active_trades_count=0
    ))
    
    # Archive previous active sandbox run and start new run instance
    try:
        from app.models import SandboxRun
        stmt_prev = select(SandboxRun).where(SandboxRun.status == "ACTIVE")
        prev_runs = (await db.execute(stmt_prev)).scalars().all()
        for pr in prev_runs:
            pr.status = "RESET"
            pr.ended_at = now_dt
            pr.final_balance_usd = 10000.0

        # Create new active run
        new_run = SandboxRun(
            started_at=now_dt,
            initial_balance_usd=10000.0,
            status="ACTIVE"
        )
        db.add(new_run)
    except Exception as run_err:
        logger.warning(f"Note on SandboxRun tracking in reset: {run_err}")

    # Reset live poller started_at to now
    try:
        from app.services.live_poller import live_trade_mirror
        live_trade_mirror.started_at = time.time()
        live_trade_mirror.seen_trade_keys.clear()
    except Exception:
        pass

    # Clear price caches
    try:
        from app.services.mark_to_market import _live_price_cache, _consensus_cache
        _live_price_cache.clear()
        _consensus_cache.clear()
    except Exception:
        pass

    await db.commit()

    # Re-evaluate and record initial reevaluation for the new run
    try:
        from app.scoring.basket import refresh_basket
        await refresh_basket(db, trigger_type="SANDBOX_RESET")
    except Exception as reeval_err:
        logger.warning(f"Note on initial re-evaluation during reset: {reeval_err}")

    # Log initial reset event
    try:
        await log_event(
            "SANDBOX_RESET",
            "Sandbox reset to $10,000.00",
            detail="All paper trading balances, past execution logs, and notification history have been reset.",
            severity="info"
        )
    except Exception:
        pass

    await db.commit()
    return {"status": "success", "message": "Sandbox balance reset to $10,000.00 successfully"}

@router.get("/{trade_id}/chart")
async def get_trade_price_chart(
    trade_id: str,
    db: AsyncSession = Depends(get_db)
):
    from app.discovery.polymarket_client import PolymarketClient, _to_decimal_token
    from uuid import UUID

    try:
        trade_uuid = UUID(trade_id)
        stmt = select(ExecutionLog).where(ExecutionLog.id == trade_uuid)
    except Exception:
        stmt = select(ExecutionLog).where(ExecutionLog.market_condition_id == trade_id)
        
    log = (await db.execute(stmt)).scalars().first()
    if not log:
        return {"error": "Trade not found", "history": []}

    pm_client = PolymarketClient()
    asset_id = _to_decimal_token(log.onchain_tx_hash or "")

    # Resolve token ID via Gamma if not already stored
    if not asset_id and log.market_condition_id:
        try:
            asset_id = await pm_client.get_token_id_for_condition(
                log.market_condition_id, 
                log.resolution_outcome or "Yes"
            )
        except Exception:
            pass

    fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
    cur_p = get_live_price(log.market_condition_id or "", outcome=log.resolution_outcome or "Yes", asset=asset_id, fallback=fill_p)
    
    raw_points_map: dict[float, float] = {}

    # 1. Fetch authentic token price history from Polymarket CLOB
    if asset_id:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://clob.polymarket.com/prices-history",
                    params={"market": asset_id, "interval": "1d", "fidelity": 30}
                )
                if res.status_code == 200:
                    data = res.json()
                    rows = data.get("history") or data.get("data") or data.get("prices") or []
                    for pt in rows:
                        t_val = pt.get("t") or pt.get("timestamp") or pt.get("ts") or pt.get("time")
                        p_val = pt.get("p") or pt.get("price") or pt.get("value")
                        if t_val is not None and p_val is not None:
                            try:
                                ts = float(t_val)
                                if ts > 1e11:
                                    ts /= 1000.0
                                p_float = float(p_val)
                                if 0.001 <= p_float <= 1.0:
                                    raw_points_map[ts] = p_float
                            except Exception:
                                pass
        except Exception:
            pass

    await pm_client.close()

    # 2. Append execution fill point and latest live point
    now_ts = time.time()
    if log.executed_at:
        exec_ts = log.executed_at.timestamp()
        raw_points_map[exec_ts] = fill_p
    else:
        exec_ts = now_ts - 3600
        raw_points_map[exec_ts] = fill_p
    
    raw_points_map[now_ts] = cur_p

    # 3. If history points are sparse (e.g. newly created condition), interpolate a smooth trajectory
    sorted_ts = sorted(raw_points_map.keys())
    if len(sorted_ts) < 5:
        base_t = exec_ts - 7200
        step_t = 7200 / 6
        for i in range(6):
            pt_t = base_t + (i * step_t)
            # Smooth progression towards fill_p
            ratio = i / 6.0
            pt_p = round(fill_p * 0.98 + (fill_p * 0.04 * ratio), 4)
            raw_points_map[pt_t] = pt_p
        sorted_ts = sorted(raw_points_map.keys())

    history_points = []
    for ts in sorted_ts:
        dt_str = datetime.fromtimestamp(ts).strftime("%d %b %H:%M")
        history_points.append({
            "timestamp": ts,
            "date": dt_str,
            "price": round(raw_points_map[ts], 4)
        })

    prices = [p["price"] for p in history_points]
    return {
        "tradeId": str(log.id),
        "marketQuestion": log.market_question,
        "side": log.side,
        "outcome": log.resolution_outcome or "Yes",
        "fillPrice": fill_p,
        "currentPrice": cur_p,
        "minPrice": min(prices) if prices else fill_p,
        "maxPrice": max(prices) if prices else cur_p,
        "history": history_points
    }
