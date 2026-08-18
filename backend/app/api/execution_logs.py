from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import ExecutionLog
from app.services.mark_to_market import get_live_price, get_consensus

router = APIRouter(prefix="/api/executions", tags=["execution_logs"])

@router.get("")
async def get_execution_logs(
    user_id: Optional[str] = Query(None, alias="userId"),
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    from app.services.polymarket_fees import calculate_polymarket_fee

    def execution_log_to_response(log) -> dict:
        cid = log.market_condition_id or ""
        outc = log.resolution_outcome or "Yes"
        fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
        cur_p = get_live_price(cid, outcome=outc, asset=log.onchain_tx_hash or "", fallback=fill_p)
        consensus = get_consensus(cid)
        notional = float(log.notional_usd or 0.0)

        # Polymarket Dynamic Fee Calculation
        fee_info = calculate_polymarket_fee(
            notional_usd=notional,
            price=fill_p,
            market_title=log.market_question or ""
        )
        fee_usd = float(log.fee_usd) if log.fee_usd is not None and log.fee_usd > 0 else fee_info["fee_usd"]
        category = log.market_category or fee_info["category"]
        
        # Calculate dynamic Gross & Net PnL
        if fill_p > 0:
            if log.side == "BUY":
                gross_pnl = notional * ((cur_p - fill_p) / fill_p)
            else:
                gross_pnl = notional * ((fill_p - cur_p) / fill_p)
        else:
            gross_pnl = 0.0

        net_pnl = log.realized_pnl_usd if log.realized_pnl_usd is not None else round(gross_pnl - fee_usd, 2)
        pnl_pct = round((net_pnl / notional) * 100.0, 1) if notional > 0 else 0.0

        return {
            "id": str(log.id),
            "timestamp": log.executed_at.isoformat() if log.executed_at else None,
            "walletAddress": log.source_wallet_address,
            "marketQuestion": log.market_question,
            "marketConditionId": cid,
            "side": log.side,
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
            "consensus": consensus,
            "polymarketUrl": f"https://polymarket.com/event/{cid}" if cid else "https://polymarket.com"
        }

    stmt = select(ExecutionLog)
    if status:
        stmt = stmt.where(ExecutionLog.status == status)
    if start_date:
        stmt = stmt.where(ExecutionLog.executed_at >= start_date)
    if end_date:
        stmt = stmt.where(ExecutionLog.executed_at <= end_date)

    if user_id:
        user_stmt = stmt.where(ExecutionLog.user_id == user_id).order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
        user_res = (await db.execute(user_stmt)).scalars().all()
        if user_res:
            return [execution_log_to_response(log) for log in user_res]

    # System-wide live feed: show deduplicated system logs
    system_stmt = stmt.where(ExecutionLog.user_id.is_(None)).order_by(ExecutionLog.executed_at.desc()).limit(limit).offset(offset)
    result = await db.execute(system_stmt)
    return [execution_log_to_response(log) for log in result.scalars().all()]


@router.get("/summary")
async def get_portfolio_summary(
    user_id: Optional[str] = Query(None, alias="userId"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExecutionLog).where(ExecutionLog.status == "FILLED")
    if user_id:
        stmt = stmt.where(ExecutionLog.user_id == user_id)
    else:
        stmt = stmt.where(ExecutionLog.user_id.is_(None))
    
    starting_balance = 10000.0
    if user_id:
        from app.models import User
        from uuid import UUID
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
    limit: int = 150,
    db: AsyncSession = Depends(get_db)
):
    from app.models import PortfolioSnapshot
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

    stmt = stmt.order_by(PortfolioSnapshot.timestamp.asc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

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
    import httpx, time
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

    # 1. Fetch authentic price history from Polymarket CLOB
    if asset_id:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://clob.polymarket.com/prices-history",
                    params={"market": asset_id, "interval": "max", "fidelity": 60}
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

    # 2. Append execution fill point and latest live point cleanly
    if log.executed_at:
        exec_ts = log.executed_at.timestamp()
        if exec_ts not in raw_points_map:
            raw_points_map[exec_ts] = fill_p
    
    now_ts = time.time()
    raw_points_map[now_ts] = cur_p

    # Format into chronological points list
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
        "fillPrice": fill_p,
        "currentPrice": cur_p,
        "minPrice": min(prices) if prices else fill_p,
        "maxPrice": max(prices) if prices else cur_p,
        "history": history_points
    }


