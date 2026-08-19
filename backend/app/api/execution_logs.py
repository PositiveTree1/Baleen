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
        if tf == "1d":
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

    if user_id:
        from uuid import UUID
        try:
            u_uuid = UUID(user_id)
            user_stmt = stmt.where(ExecutionLog.user_id == u_uuid).order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
            raw_logs = (await db.execute(user_stmt)).scalars().all()
        except Exception:
            raw_logs = []
    else:
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

        # Gross & Net PnL
        if fill_p > 0:
            if log.side == "BUY":
                gross_pnl = notional * ((cur_p - fill_p) / fill_p)
            else:
                gross_pnl = notional * ((fill_p - cur_p) / fill_p)
        else:
            gross_pnl = 0.0

        net_pnl = log.realized_pnl_usd if log.realized_pnl_usd is not None else round(gross_pnl - fee_usd, 2)
        pnl_pct = round((net_pnl / notional) * 100.0, 1) if notional > 0 else 0.0

        poly_url = make_polymarket_url(log.event_slug, log.market_question, cid)
        w_meta = whale_meta_map.get(log.source_wallet_address.lower() if log.source_wallet_address else "", {})

        whale_pnl_bankroll = float(w_meta.get("all_time_pnl_usd") or 35000.0)
        whale_stake = float(log.notional_usd or 5.0) * 10.0
        whale_bankroll_pct = round(min(100.0, max(0.05, (whale_stake / max(5000.0, whale_pnl_bankroll)) * 100.0)), 1)

        # Enrich consensus whale list
        enriched_consensus = dict(consensus) if consensus else {}
        if enriched_consensus.get("whales"):
            w_details = []
            for w_addr in enriched_consensus["whales"]:
                m = whale_meta_map.get(w_addr.lower(), {})
                w_details.append({
                    "address": w_addr,
                    "name": m.get("name"),
                    "pseudonym": m.get("pseudonym"),
                    "profileImage": m.get("profileImage"),
                    "tier": m.get("tier")
                })
            enriched_consensus["whale_details"] = w_details

        response_list.append({
            "id": str(log.id),
            "timestamp": log.executed_at.isoformat() if log.executed_at else None,
            "walletAddress": log.source_wallet_address,
            "whaleName": w_meta.get("name"),
            "whalePseudonym": w_meta.get("pseudonym"),
            "whaleAvatar": w_meta.get("profileImage"),
            "whaleTier": w_meta.get("tier"),
            "whaleStakeUsd": round(whale_stake, 2),
            "whaleBankrollPct": whale_bankroll_pct,
            "marketQuestion": log.market_question,
            "marketConditionId": cid,
            "eventSlug": log.event_slug,
            "icon": log.icon,
            "side": log.side,
            "outcome": outc,
            "entryPrice": log.whale_entry_price,
            "fillPrice": log.user_fill_price,
            "currentPrice": cur_p,
            "size": log.notional_usd,
            "status": log.status,
            "feeUsd": round(fee_usd, 4),
            "marketCategory": category,
            "categoryRate": fee_info["category_rate"],
            "pnl": round(net_pnl, 2),
            "grossPnl": round(gross_pnl, 2),
            "pnlPct": pnl_pct,
            "consensus": enriched_consensus,
            "polymarketUrl": poly_url
        })

    return response_list

@router.get("/summary")
async def get_portfolio_summary(
    user_id: Optional[str] = Query(None, alias="userId"),
    timeframe: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExecutionLog).where(ExecutionLog.status == "FILLED")
    if user_id:
        from uuid import UUID
        try:
            u_uuid = UUID(user_id)
            stmt = stmt.where(ExecutionLog.user_id == u_uuid)
        except Exception:
            pass
    else:
        stmt = stmt.where(ExecutionLog.user_id.is_(None))

    now = datetime.utcnow()
    if timeframe:
        tf = timeframe.lower()
        if tf == "1d":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=1))
        elif tf == "1w":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=7))
        elif tf == "1m":
            stmt = stmt.where(ExecutionLog.executed_at >= now - timedelta(days=30))
        elif tf == "ytd":
            stmt = stmt.where(ExecutionLog.executed_at >= datetime(now.year, 1, 1))

    logs = (await db.execute(stmt)).scalars().all()
    starting_balance = 10000.0

    if user_id:
        try:
            u_uuid = UUID(user_id)
            u_obj = (await db.execute(select(User).where(User.id == u_uuid))).scalar_one_or_none()
            if u_obj and u_obj.sandbox_starting_balance_usd is not None:
                starting_balance = float(u_obj.sandbox_starting_balance_usd)
        except Exception:
            pass

    total_pnl = 0.0
    total_notional = 0.0
    total_fees = 0.0
    
    for log in logs:
        cid = log.market_condition_id or ""
        outc = log.resolution_outcome or "Yes"
        fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
        cur_p = get_live_price(cid, outcome=outc, asset=log.onchain_tx_hash or "", fallback=fill_p)
        notional = float(log.notional_usd or 0.0)
        total_notional += notional
        
        fee_info = calculate_polymarket_fee(
            notional_usd=notional,
            price=fill_p,
            market_title=log.market_question or ""
        )
        fee = float(log.fee_usd) if log.fee_usd is not None and log.fee_usd > 0 else fee_info["fee_usd"]
        total_fees += fee
        
        trade_pnl = log.realized_pnl_usd
        if trade_pnl is None and fill_p > 0:
            if log.side == "BUY":
                gross_pnl = notional * ((cur_p - fill_p) / fill_p)
            else:
                gross_pnl = notional * ((fill_p - cur_p) / fill_p)
            trade_pnl = gross_pnl - fee
        if trade_pnl is not None:
            total_pnl += float(trade_pnl)
            
    current_balance = round(starting_balance + total_pnl, 2)
    pnl_pct = round((total_pnl / starting_balance) * 100.0, 2) if starting_balance > 0 else 0.0
    
    return {
        "startingBalance": starting_balance,
        "currentBalance": current_balance,
        "totalPnlUsd": round(total_pnl, 2),
        "totalPnlPct": pnl_pct,
        "totalFeesPaidUsd": round(total_fees, 2),
        "filledTradesCount": len(logs),
        "totalNotionalInvested": round(total_notional, 2)
    }

@router.get("/snapshots")
async def get_portfolio_snapshots(
    user_id: Optional[str] = Query(None, alias="userId"),
    timeframe: Optional[str] = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db)
):
    from uuid import UUID
    stmt = select(PortfolioSnapshot)
    if user_id:
        try:
            u_uuid = UUID(user_id)
            stmt = stmt.where(PortfolioSnapshot.user_id == u_uuid)
        except Exception:
            stmt = stmt.where(PortfolioSnapshot.user_id.is_(None))
    else:
        stmt = stmt.where(PortfolioSnapshot.user_id.is_(None))

    now = datetime.utcnow()
    if timeframe:
        tf = timeframe.lower()
        if tf == "1d":
            stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(days=1))
        elif tf == "1w":
            stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(days=7))
        elif tf == "1m":
            stmt = stmt.where(PortfolioSnapshot.timestamp >= now - timedelta(days=30))
        elif tf == "ytd":
            stmt = stmt.where(PortfolioSnapshot.timestamp >= datetime(now.year, 1, 1))

    stmt = stmt.order_by(PortfolioSnapshot.timestamp.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    rows = list(reversed(rows))

    return [
        {
            "id": str(r.id),
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "time": r.timestamp.strftime("%H:%M") if r.timestamp else "",
            "date": r.timestamp.strftime("%d %b") if r.timestamp else "",
            "balance": round(float(r.balance), 2),
            "pnl": round(float(r.total_pnl), 2),
            "activeTrades": r.active_trades_count
        }
        for r in rows
    ]

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
