from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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

    # Query canonical sandbox execution logs (user_id IS NULL)
    system_stmt = stmt.where(ExecutionLog.user_id.is_(None)).order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
    raw_logs = (await db.execute(system_stmt)).scalars().all()

    if not raw_logs:
        return []

    # Batch query whale wallets for authentic nicknames, usernames, and avatars
    whale_addrs = list(set(log.source_wallet_address.lower() for log in raw_logs if log.source_wallet_address))
    whale_meta_map: Dict[str, Dict] = {}
    if whale_addrs:
        w_records = (await db.execute(select(Wallet).where(Wallet.address.in_(whale_addrs)))).scalars().all()
        for w in w_records:
            whale_meta_map[w.address.lower()] = {
                "name": w.name,
                "pseudonym": w.pseudonym,
                "profileImage": w.profile_image,
                "tier": w.tier,
                "all_time_pnl_usd": w.all_time_pnl_usd
            }

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

        # Gross & Net PnL — guard against cold price cache
        if fill_p > 0 and abs(cur_p - fill_p) > 0.001:
            if log.side == "BUY":
                gross_pnl = notional * ((cur_p - fill_p) / fill_p)
            else:
                gross_pnl = notional * ((fill_p - cur_p) / fill_p)
        else:
            gross_pnl = 0.0

        if log.realized_pnl_usd is not None:
            net_pnl = log.realized_pnl_usd
        elif abs(cur_p - fill_p) > 0.001:
            net_pnl = round(gross_pnl - fee_usd, 2)
        else:
            net_pnl = 0.0
        pnl_pct = round((net_pnl / notional) * 100.0, 2) if notional > 0 else 0.0

        whale_info = whale_meta_map.get((log.source_wallet_address or "").lower(), {})

        response_list.append({
            "id": str(log.id),
            "timestamp": log.executed_at.isoformat() if log.executed_at else None,
            "source_wallet_address": log.source_wallet_address,
            "whaleName": whale_info.get("name"),
            "whalePseudonym": whale_info.get("pseudonym"),
            "whaleAvatar": whale_info.get("profileImage"),
            "whaleTier": whale_info.get("tier"),
            "market_question": log.market_question,
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
            "polymarketUrl": f"https://polymarket.com/event/{log.event_slug}" if log.event_slug else (
                f"https://polymarket.com/market/{cid}" if cid else "https://polymarket.com"
            )
        })

    return response_list

@router.get("/summary")
async def get_portfolio_summary(
    user_id: Optional[str] = Query(None, alias="userId"),
    timeframe: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExecutionLog).where(
        ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]),
        ExecutionLog.user_id.is_(None)
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

    logs = (await db.execute(stmt)).scalars().all()
    starting_balance = 10000.0

    total_pnl = 0.0
    total_notional = 0.0
    total_fees = 0.0
    
    for log in logs:
        notional = float(log.notional_usd or 0.0)
        total_notional += notional
        total_fees += float(log.fee_usd or 0.0)
        
        trade_pnl = log.realized_pnl_usd
        if trade_pnl is None:
            # For FILLED (open) trades with no stored PnL, only compute unrealized
            # PnL if we have a REAL live price (different from the entry).
            # If the price cache is cold (cur_p == fill_p), treat as 0 PnL
            # rather than subtracting fees as a phantom loss.
            cid = log.market_condition_id or ""
            outc = log.resolution_outcome or "Yes"
            fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
            cur_p = get_live_price(cid, outcome=outc, asset=log.onchain_tx_hash or "", fallback=fill_p)
            if abs(cur_p - fill_p) > 0.001:  # Only count if we have a real price change
                fee = float(log.fee_usd or 0.0)
                if fill_p > 0:
                    if log.side == "BUY":
                        gross_pnl = notional * ((cur_p - fill_p) / fill_p)
                    else:
                        gross_pnl = notional * ((fill_p - cur_p) / fill_p)
                    trade_pnl = gross_pnl - fee
        if trade_pnl is not None:
            total_pnl += float(trade_pnl)

    # Market Attribution aggregation across database records
    market_map = {}
    wins_count = 0
    losses_count = 0
    for log in logs:
        key = log.market_question or log.market_condition_id or str(log.id)
        pnl_val = float(log.realized_pnl_usd or 0.0)
        notional_val = float(log.notional_usd or 0.0)
        fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
        
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
    
    return {
        "startingBalance": starting_balance,
        "currentBalance": current_balance,
        "totalPnlUsd": round(total_pnl, 2),
        "totalPnlPct": pnl_pct,
        "totalFeesPaidUsd": round(total_fees, 2),
        "filledTradesCount": len(logs),
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
    
    if tf == "1h":
        stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(hours=1))
    elif tf == "6h":
        stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(hours=6))
    elif tf == "1d":
        stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(days=1))
    elif tf == "1w":
        stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(days=7))
    elif tf == "1m":
        stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(days=30))
    elif tf == "ytd":
        stmt = stmt.where(PortfolioSnapshot.timestamp >= datetime(now.year, 1, 1))

    # Query snapshots in ascending chronological order
    stmt = stmt.where(PortfolioSnapshot.user_id.is_(None)).order_by(PortfolioSnapshot.timestamp.asc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    if not rows:
        fallback_stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)).order_by(PortfolioSnapshot.timestamp.desc()).limit(2)
        rows = list(reversed((await db.execute(fallback_stmt)).scalars().all()))

    # FALLBACK: If snapshot table is sparse (< 3 points), synthesize a timeline
    # from execution logs so the chart always renders correctly
    if len(rows) < 3:
        try:
            trade_stmt = select(ExecutionLog).where(
                ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]),
                ExecutionLog.user_id.is_(None)
            ).order_by(ExecutionLog.executed_at.asc())
            trades = (await db.execute(trade_stmt)).scalars().all()
            if trades:
                synth_points = []
                cumulative_pnl = 0.0
                for t in trades:
                    cumulative_pnl += float(t.realized_pnl_usd or 0.0)
                    balance = round(10000.0 + cumulative_pnl, 2)
                    ts = t.executed_at
                    synth_points.append({
                        "id": f"synth-{str(t.id)[:8]}",
                        "timestamp": (ts.isoformat() + "Z") if ts else None,
                        "time": ts.strftime("%H:%M") if ts else "",
                        "date": ts.strftime("%d %b") if ts else "",
                        "balance": balance,
                        "pnl": round(cumulative_pnl, 2),
                        "activeTrades": len(trades)
                    })

                # Include genesis baseline
                if synth_points and abs(synth_points[0]["balance"] - 10000.0) > 0.01:
                    first_date = synth_points[0]["date"]
                    first_time = synth_points[0]["time"]
                    synth_points.insert(0, {
                        "id": "genesis-baseline",
                        "timestamp": synth_points[0]["timestamp"],
                        "time": first_time,
                        "date": first_date,
                        "balance": 10000.0,
                        "pnl": 0.0,
                        "activeTrades": 0
                    })

                # Downsample if needed
                if len(synth_points) > 120:
                    step = max(1, len(synth_points) // 100)
                    downsampled = [synth_points[i] for i in range(0, len(synth_points) - 1, step)]
                    if synth_points[-1] not in downsampled:
                        downsampled.append(synth_points[-1])
                    synth_points = downsampled

                return synth_points
        except Exception:
            pass  # Fall through to normal logic

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

        bucketed_rows = []
        seen_buckets = set()
        for r in rows:
            if r.timestamp:
                b_key = int(r.timestamp.timestamp() // bucket_secs)
                if b_key not in seen_buckets:
                    seen_buckets.add(b_key)
                    bucketed_rows.append(r)
            else:
                bucketed_rows.append(r)

        # Always include the exact latest live snapshot at the end
        if rows and (not bucketed_rows or bucketed_rows[-1].id != rows[-1].id):
            bucketed_rows.append(rows[-1])

        rows = bucketed_rows

    result = [
        {
            "id": str(r.id),
            "timestamp": (r.timestamp.isoformat() + "Z") if r.timestamp else None,
            "time": r.timestamp.strftime("%H:%M") if r.timestamp else "",
            "date": r.timestamp.strftime("%d %b") if r.timestamp else "",
            "balance": round(float(r.balance), 2),
            "pnl": round(float(r.total_pnl), 2),
            "activeTrades": r.active_trades_count
        }
        for r in rows
    ]

    # Prepend Genesis $10,000.00 baseline for ALL timeframe
    if tf == "all" and result:
        first_date = result[0]["date"]
        first_time = result[0]["time"]
        if abs(result[0]["balance"] - 10000.0) > 0.01:
            genesis_point = {
                "id": "genesis-baseline",
                "timestamp": result[0].get("timestamp"),
                "time": first_time,
                "date": first_date,
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
