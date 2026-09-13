import uuid
import re
import time
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import ExecutionLog, Wallet, User, PortfolioSnapshot
from app.auth import get_current_user, get_current_user_optional
from app.services.mark_to_market import get_live_price, get_consensus
from app.services.polymarket_fees import calculate_polymarket_fee

router = APIRouter(prefix="/api/executions", tags=["execution_logs"])

def _resolve_user_id(user_id: Any, userId: Any = None) -> Optional[str]:
    """Extracts valid user_id string, ignoring default FastAPI Query/Depends sentinel objects."""
    if isinstance(user_id, (str, uuid.UUID)):
        s = str(user_id).strip()
        if s and not s.startswith("Query(") and not s.startswith("<fastapi."):
            return s
    if isinstance(userId, (str, uuid.UUID)):
        s = str(userId).strip()
        if s and not s.startswith("Query(") and not s.startswith("<fastapi."):
            return s
    return None

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
    userId: Optional[str] = Query(None),
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    timeframe: Optional[str] = None, # 1d, 1w, 1m, ytd, all
    limit: int = Query(1500, le=10000),
    offset: int = 0,
    current_user: Optional[User] = Depends(get_current_user_optional),
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

    eff_user_id = _resolve_user_id(user_id, userId)
    if not isinstance(current_user, User):
        current_user = None

    if eff_user_id:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            u_uuid = uuid.UUID(eff_user_id)
        except Exception:
            raise HTTPException(status_code=404, detail="User not found")
        if str(current_user.id) != str(u_uuid) and not (getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"):
            raise HTTPException(status_code=403, detail="Forbidden: access to another account is denied")
        user_filter = ExecutionLog.user_id == u_uuid
    else:
        user_filter = ExecutionLog.user_id.is_(None)

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
        from app.services.execution_valuation import execution_valuation
        valuation = execution_valuation(log)
        fill_p, cur_p = valuation['fillPrice'], valuation['currentPrice']
        fee_usd, net_pnl, gross_pnl = valuation['feeUsd'], valuation['pnl'], valuation['grossPnl']
        pnl_pct = valuation['pnlPct']
        consensus = get_consensus(cid)
        notional = log.notional_usd
        category = log.market_category

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
            "grossPnl": gross_pnl,
            "markStatus": valuation["markStatus"],
            "markObservedAt": valuation["markObservedAt"],
            "pnlPct": pnl_pct,
            "feeUsd": fee_usd,
            "marketCategory": category,
            "categoryRate": None,
            "consensus": consensus,
            "polymarketUrl": make_polymarket_url(log.event_slug, log.market_question, cid)
        })

    return response_list

@router.get("/summary")
async def get_portfolio_summary(
    user_id: Optional[str] = Query(None, alias="userId"),
    userId: Optional[str] = Query(None),
    timeframe: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    eff_user_id = _resolve_user_id(user_id, userId)
    if not isinstance(current_user, User):
        current_user = None
    target_user = None
    if eff_user_id:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            u_uuid = uuid.UUID(eff_user_id)
        except Exception:
            raise HTTPException(status_code=404, detail="User not found")
        if str(current_user.id) != str(u_uuid) and not (getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"):
            raise HTTPException(status_code=403, detail="Forbidden: access to another account is denied")
        target_user = await db.get(User, u_uuid)
        user_filter = ExecutionLog.user_id == u_uuid
    else:
        user_filter = ExecutionLog.user_id.is_(None)

    from app.models import SandboxRun
    from app.services.execution_valuation import execution_valuation, finite
    if eff_user_id and target_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    logs = (await db.execute(select(ExecutionLog).where(user_filter,
        ExecutionLog.is_sandbox.is_(True), ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"])))) .scalars().all()
    if target_user:
        starting_balance = finite(target_user.sandbox_starting_balance_usd)
    else:
        run = (await db.execute(select(SandboxRun).where(SandboxRun.user_id.is_(None),
            SandboxRun.status == 'ACTIVE').order_by(SandboxRun.started_at.desc()).limit(1))).scalar_one_or_none()
        starting_balance = finite(run.initial_balance_usd) if run else None
    # BUY lots own position P&L. SELL rows record exit cash/fees, not another return.
    positions = [r for r in logs if r.side == 'BUY']
    values = {r.id: execution_valuation(r) for r in positions}
    unvalued = sum(values[r.id]['pnl'] is None for r in positions)
    known_pnl = sum(values[r.id]['pnl'] for r in positions if values[r.id]['pnl'] is not None)
    total_pnl = None if unvalued else round(known_pnl, 2)
    effective_pnl = total_pnl if total_pnl is not None else round(known_pnl, 2)
    current_balance = round(starting_balance + effective_pnl, 2) if starting_balance is not None else None
    now = datetime.utcnow()
    windows = {'1h': timedelta(hours=1), '6h': timedelta(hours=6), '1d': timedelta(days=1),
               '1w': timedelta(days=7), '1m': timedelta(days=30)}
    tf = (timeframe or 'all').lower()
    since = now - windows[tf] if tf in windows else datetime(now.year, 1, 1) if tf == 'ytd' else None
    selected = [r for r in positions if since is None or (r.executed_at and r.executed_at >= since)]
    fee_rows = [r for r in logs if since is None or (r.executed_at and r.executed_at >= since)]
    fees = [finite(r.fee_usd) for r in fee_rows]
    notionals = [finite(r.notional_usd) for r in selected]
    market_map = {}
    wins = losses = 0
    for row in selected:
        value = values[row.id]
        # Classify completed outcomes only; floating marks are not a win rate.
        if row.status in ('CLOSED', 'RESOLVED') and value['pnl'] is not None:
            wins += value['pnl'] > 0
            losses += value['pnl'] < 0
        key = (row.market_condition_id, row.resolution_outcome)
        market = market_map.setdefault(key, {'key': ':'.join(str(v or '') for v in key),
            'question': row.market_question, 'conditionId': row.market_condition_id,
            'outcome': row.resolution_outcome, 'totalPnl': 0.0, 'totalNotional': 0.0,
            'fillsCount': 0, 'avgFillPrice': None, 'unvaluedTradesCount': 0})
        market['fillsCount'] += 1
        if value['pnl'] is None:
            market['unvaluedTradesCount'] += 1
        else:
            market['totalPnl'] += value['pnl']
        notional = finite(row.notional_usd)
        market['totalNotional'] = (market['totalNotional'] + notional
            if market['totalNotional'] is not None and notional is not None else None)
    complete_markets = [m for m in market_map.values() if not m['unvaluedTradesCount']]
    known_fees = sum(f for f in fees if f is not None)
    holding = sum(r.status == 'FILLED' for r in selected)
    return {
        'startingBalance': starting_balance, 'currentBalance': current_balance,
        'totalPnlUsd': total_pnl,
        'totalPnlPct': round(total_pnl / starting_balance * 100, 2) if total_pnl is not None and starting_balance else None,
        'valuationStatus': 'INCOMPLETE' if unvalued or starting_balance is None else 'COMPLETE',
        'unvaluedTradesCount': unvalued, 'knownPnlUsd': round(known_pnl, 2),
        'totalFeesPaidUsd': round(known_fees, 2) if all(f is not None for f in fees) else None,
        'knownFeesPaidUsd': round(known_fees, 2),
        'filledTradesCount': len(selected), 'holdingTradesCount': holding,
        'closedTradesCount': len(selected) - holding,
        'totalNotionalInvested': round(sum(notionals), 2) if all(n is not None for n in notionals) else None,
        'topAlphaMarkets': sorted([m for m in complete_markets if m['totalPnl'] > 0], key=lambda m: m['totalPnl'], reverse=True)[:5],
        'topDrawdownMarkets': sorted([m for m in complete_markets if m['totalPnl'] < 0], key=lambda m: m['totalPnl'])[:5],
        'allTimeWinRate': round(wins / (wins + losses) * 100, 1) if wins + losses else None,
        'allTimeWins': wins, 'allTimeLosses': losses,
        'statisticsTimeframe': tf,
    }

@router.get("/snapshots")
async def get_portfolio_snapshots(
    user_id: Optional[str] = Query(None, alias="userId"),
    userId: Optional[str] = Query(None),
    timeframe: Optional[str] = None,
    limit: int = 5000,
    current_user: Optional[User] = Depends(get_current_user_optional),
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

    eff_user_id = _resolve_user_id(user_id, userId)
    if not isinstance(current_user, User):
        current_user = None

    if eff_user_id:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            u_uuid = uuid.UUID(eff_user_id)
        except Exception:
            raise HTTPException(status_code=404, detail="User not found")
        if str(current_user.id) != str(u_uuid) and not (getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"):
            raise HTTPException(status_code=403, detail="Forbidden: access to another account is denied")
        user_filter = PortfolioSnapshot.user_id == u_uuid
    else:
        user_filter = PortfolioSnapshot.user_id.is_(None)

    stmt = stmt.where(user_filter).order_by(PortfolioSnapshot.timestamp.asc())
    rows = list((await db.execute(stmt)).scalars().all())

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
        ts_clean = r.timestamp

        result.append({
            "id": str(r.id),
            "timestamp": (ts_clean.isoformat() + "Z") if ts_clean else None,
            "time": ts_clean.strftime("%H:%M") if ts_clean else "",
            "date": ts_clean.strftime("%d %b") if ts_clean else "",
            "balance": round(float(r.balance), 2),
            "pnl": round(float(r.total_pnl), 2),
            "activeTrades": r.active_trades_count
        })

    return result

@router.post("/reset-sandbox")
async def reset_sandbox(
    user_id: Optional[str] = Query(None, alias="userId"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resets paper trading sandbox balance to $10,000.00 for the authenticated user.
    Strictly isolated: does NOT delete live records, other users' state, or global ingestion cursors.
    """
    from sqlalchemy import delete
    import uuid

    if not isinstance(current_user, User):
        raise HTTPException(status_code=401, detail="Authentication required to reset sandbox")

    target_user = current_user
    eff_user_id = _resolve_user_id(user_id)
    if eff_user_id:
        try:
            target_uid = uuid.UUID(eff_user_id)
        except Exception:
            raise HTTPException(status_code=404, detail="User not found")
        target_user = await db.get(User, target_uid)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        is_admin = getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"
        if str(current_user.id) != str(target_user.id) and not is_admin:
            raise HTTPException(status_code=403, detail="Forbidden: cannot reset another user's sandbox")

    from app.services.paper_runs import archive_and_start
    run = await archive_and_start(db, target_user, 10000)

    await db.commit()
    await db.refresh(target_user)
    return {
        "status": "success",
        "message": "Previous paper run archived; new $10,000.00 paper run started",
        "runId": str(run.id),
        "userId": str(target_user.id)
    }

@router.get("/{trade_id}/chart")
async def get_trade_price_chart(
    trade_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    from app.discovery.polymarket_client import PolymarketClient
    from uuid import UUID

    try:
        trade_uuid = UUID(trade_id)
        stmt = select(ExecutionLog).where(ExecutionLog.id == trade_uuid)
    except Exception:
        stmt = select(ExecutionLog).where(ExecutionLog.market_condition_id == trade_id)
        stmt = stmt.where(ExecutionLog.user_id == current_user.id if current_user else ExecutionLog.user_id.is_(None))
        
    log = (await db.execute(stmt)).scalars().first()
    if not log:
        raise HTTPException(status_code=404, detail="Trade not found")

    if log.user_id is not None:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if str(log.user_id) != str(current_user.id) and not (getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"):
            raise HTTPException(status_code=403, detail="Access to another account's trade is forbidden")

    pm_client = PolymarketClient()
    asset_id = log.token_id or ""

    # Resolve token ID via Gamma if not already stored
    if not asset_id and log.market_condition_id:
        try:
            asset_id = await pm_client.get_token_id_for_condition(
                log.market_condition_id, 
                log.resolution_outcome or "Yes"
            )
        except Exception:
            pass

    from app.services.execution_valuation import finite
    from app.services.mark_to_market import get_observed_price
    fill_p = finite(log.user_fill_price)
    observed = get_observed_price(log.market_condition_id or '', log.resolution_outcome or '', asset_id)
    cur_p = observed['price'] if observed else None
    
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
                        p_val = next((pt[k] for k in ("p", "price", "value") if pt.get(k) is not None), None)
                        if t_val is not None and p_val is not None:
                            try:
                                ts = float(t_val)
                                if ts > 1e11:
                                    ts /= 1000.0
                                p_float = float(p_val)
                                if 0.0 <= p_float <= 1.0:
                                    raw_points_map[ts] = p_float
                            except Exception:
                                pass
        except Exception:
            pass

    await pm_client.close()

    # Market history contains provider observations only. A simulated fill is
    # separate execution evidence, not a historical venue-price observation.
    if observed:
        raw_points_map[observed['observed_at']] = observed['price']

    # Sparse history remains sparse; fabricated prices misrepresent observed risk.
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
        "minPrice": min(prices) if prices else None,
        "maxPrice": max(prices) if prices else None,
        "markStatus": 'observed' if observed else 'unavailable',
        "historyStatus": 'observed' if prices else 'unavailable',
        "history": history_points
    }
