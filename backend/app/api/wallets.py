import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.analysis.ai_summary import generate_summary
from app.database import get_db
from app.models import ExecutionLog, Wallet, WalletSnapshot
from app.services.mark_to_market import _last_known_pnl, get_live_price
from app.services.polymarket_fees import calculate_polymarket_fee

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wallets", tags=["wallets"])

def wallet_to_response(w: Wallet) -> dict:
    return {
        "address": w.address,
        "name": w.name,
        "pseudonym": w.pseudonym,
        "profileImage": w.profile_image,
        "tier": w.tier or "standard",
        "win_rate_pct": w.win_rate_pct or 0.0,
        "wilson_lb": getattr(w, "wilson_lb", None),
        "all_time_pnl_usd": w.all_time_pnl_usd or 0.0,
        "avg_trades_per_day": w.avg_trades_per_day or 0.0,
        "trades_per_hour": getattr(w, "trades_per_hour", None),
        "baleen_score": w.baleen_score or 0.0,
        "ai_style_tag": w.ai_style_tag,
        "ai_summary": w.ai_summary,
        "max_drawdown_pct": w.max_drawdown_pct or 0.0,
        "outlier_concentration_pct": w.outlier_concentration_pct or 0.0,
        "alpha_per_trade": getattr(w, "alpha_per_trade", None),
        "profit_factor": getattr(w, "profit_factor", None),
        "status": w.status or "active",
        "dormant": bool(w.dormant),
        "is_hft": bool(getattr(w, "is_hft", False)),
        "first_trade_at": w.first_trade_at.isoformat() if getattr(w, "first_trade_at", None) else None,
        "last_trade_at": w.last_trade_at.isoformat() if getattr(w, "last_trade_at", None) else None,
        "total_trades_analyzed": w.total_trades_analyzed or 0,
        "avg_hold_hours": getattr(w, "median_inter_trade_gap_hours", 12.0) or 12.0,
        "rejection_reason": w.rejection_reason,
        "first_seen_at": w.first_seen_at.isoformat() if w.first_seen_at else None,
        "last_scored_at": w.last_scored_at.isoformat() if w.last_scored_at else None,
    }

@router.get("")
async def list_wallets(
    tier: Optional[str] = None,
    dormant: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Wallet).where(
        Wallet.status == "active",
        Wallet.is_hft == False
    )
    
    if dormant is not None:
        stmt = stmt.where(Wallet.dormant == dormant)
    else:
        # Default: only show active non-dormant whales on user dashboard
        stmt = stmt.where(Wallet.dormant == False)
        
    if tier:
        stmt = stmt.where(Wallet.tier == tier)
        
    stmt = stmt.order_by(Wallet.baleen_score.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [wallet_to_response(w) for w in result.scalars().all()]

@router.get("/copied-stats")
async def get_copied_wallet_stats(
    user_id: Optional[str] = Query(None, alias="userId"),
    userId: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    from uuid import UUID

    stmt = select(ExecutionLog).where(ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]))
    eff_user_id = user_id or userId
    if eff_user_id:
        try:
            u_uuid = UUID(eff_user_id)
            stmt_user = stmt.where(ExecutionLog.user_id == u_uuid)
            user_logs = (await db.execute(stmt_user)).scalars().all()
            if user_logs:
                logs = user_logs
            else:
                stmt_global = stmt.where(ExecutionLog.user_id.is_(None))
                logs = (await db.execute(stmt_global)).scalars().all()
        except Exception:
            stmt_global = stmt.where(ExecutionLog.user_id.is_(None))
            logs = (await db.execute(stmt_global)).scalars().all()
    else:
        stmt_global = stmt.where(ExecutionLog.user_id.is_(None))
        logs = (await db.execute(stmt_global)).scalars().all()

    # Track BUY keys to deduplicate paired round-trip trades
    # In live_poller, a closed position updates the BUY lot with realized_pnl_usd AND creates an exit SELL log.
    # To avoid double-counting trades_copied, total_notional, net_pnl, and wins/losses, skip the SELL log when a BUY exists.
    buy_keys = {
        ((l.source_wallet_address or "").lower(), l.market_condition_id)
        for l in logs
        if l.side != "SELL" and l.source_wallet_address and l.market_condition_id
    }

    wallet_stats = {}
    for log in logs:
        addr = (log.source_wallet_address or "unknown").lower()

        # Skip SELL exit log if the original BUY lot is present to prevent doubling
        if log.side == "SELL" and (addr, log.market_condition_id) in buy_keys:
            continue

        if addr not in wallet_stats:
            wallet_stats[addr] = {
                "address": log.source_wallet_address or addr,
                "trades_copied": 0,
                "total_notional": 0.0,
                "net_pnl": 0.0,
                "wins": 0,
                "losses": 0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
            }
        
        notional = float(log.notional_usd or 0.0)
        wallet_stats[addr]["trades_copied"] += 1
        wallet_stats[addr]["total_notional"] += notional

        # Determine trade PnL: Realized for closed/resolved trades, Mark-to-Market for open (FILLED) trades
        if log.status != "FILLED" and log.realized_pnl_usd is not None:
            pnl = float(log.realized_pnl_usd)
        elif log.status == "FILLED":
            log_id_str = str(log.id)
            if log_id_str in _last_known_pnl:
                pnl = float(_last_known_pnl[log_id_str])
            else:
                fill_p = float(log.user_fill_price or log.whale_entry_price or 0.5)
                fee = float(log.fee_usd or 0.0)
                if fee == 0.0 and notional > 0:
                    fee_info = calculate_polymarket_fee(
                        notional_usd=notional,
                        price=fill_p,
                        market_title=log.market_question or ""
                    )
                    fee = float(fee_info["fee_usd"])

                cid = log.market_condition_id or ""
                outc = log.resolution_outcome or "Yes"
                asset_id = log.onchain_tx_hash or ""
                cur_p = get_live_price(cid=cid, outcome=outc, asset=asset_id, fallback=fill_p)
                if fill_p > 0 and cur_p > 0:
                    if log.side == "BUY":
                        gross_pnl = notional * ((cur_p - fill_p) / fill_p)
                    else:
                        gross_pnl = notional * ((fill_p - cur_p) / fill_p)
                    pnl = round(gross_pnl - fee, 2)
                else:
                    pnl = round(-fee, 2)
        elif log.realized_pnl_usd is not None:
            pnl = float(log.realized_pnl_usd)
        else:
            pnl = 0.0

        wallet_stats[addr]["net_pnl"] += pnl

        if pnl > 0:
            wallet_stats[addr]["wins"] += 1
            wallet_stats[addr]["gross_profit"] += pnl
        elif pnl < 0:
            wallet_stats[addr]["losses"] += 1
            wallet_stats[addr]["gross_loss"] += abs(pnl)

    addrs = list(wallet_stats.keys())
    w_meta_map = {}
    if addrs:
        w_stmt = select(Wallet).where(func.lower(Wallet.address).in_([a.lower() for a in addrs]))
        w_rows = (await db.execute(w_stmt)).scalars().all()
        for w in w_rows:
            w_meta_map[w.address.lower()] = w

    results = []
    for addr, stats in wallet_stats.items():
        w_obj = w_meta_map.get(addr.lower())
        total_resolved = stats["wins"] + stats["losses"]
        wr = (stats["wins"] / total_resolved * 100.0) if total_resolved > 0 else 0.0
        pf = (stats["gross_profit"] / stats["gross_loss"]) if stats["gross_loss"] > 0 else (10.0 if stats["gross_profit"] > 0 else 1.0)
        roi = (stats["net_pnl"] / stats["total_notional"] * 100.0) if stats["total_notional"] > 0 else 0.0

        disp_name = (w_obj.name if w_obj and w_obj.name else (w_obj.pseudonym if w_obj and w_obj.pseudonym else None))
        copy_rate = 100.0

        results.append({
            "address": stats["address"],
            "name": disp_name or f"{stats['address'][:6]}...{stats['address'][-4:]}",
            "pseudonym": w_obj.pseudonym if w_obj else None,
            "profileImage": w_obj.profile_image if w_obj else None,
            "tier": w_obj.tier if w_obj else "standard",
            "score": w_obj.baleen_score if w_obj else None,
            "aiStyleTag": w_obj.ai_style_tag if w_obj else "Tactical Whale",
            "tradesCopied": stats["trades_copied"],
            "fillsCount": stats["trades_copied"],
            "totalNotional": round(stats["total_notional"], 2),
            "netPnl": round(stats["net_pnl"], 2),
            "mirroredPnl": round(stats["net_pnl"], 2),
            "roiPct": round(roi, 2),
            "winRateCopied": round(wr, 1),
            "profitFactor": round(pf, 2),
            "wins": stats["wins"],
            "losses": stats["losses"],
            "copyRatePct": copy_rate,
        })

    results.sort(key=lambda r: r["netPnl"], reverse=True)
    return results

@router.get("/{address}")
async def get_wallet(address: str, db: AsyncSession = Depends(get_db)):
    clean_addr = address.lower()
    
    # Wallet query (case insensitive)
    stmt = select(Wallet).where(func.lower(Wallet.address) == clean_addr)
    wallet = (await db.execute(stmt)).scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
        
    # Clean corrupted AI summary if it contains leaked prompt artifacts
    is_corrupted = False
    if wallet.ai_summary:
        bad_markers = ["Metrics Provided:", "<2 punchy", "TAG:", "Deconstruct Metrics", "Output format EXACTLY", "<2-3 word"]
        if any(marker in wallet.ai_summary for marker in bad_markers):
            is_corrupted = True
            wallet.ai_summary = None

    # Auto-generate clean AI summary on-demand if missing or corrupted
    if not wallet.ai_summary or not wallet.ai_style_tag or is_corrupted:
        try:
            stats_dict = {
                "win_rate_pct": wallet.win_rate_pct or 0.0,
                "all_time_pnl_usd": wallet.all_time_pnl_usd or 0.0,
                "avg_trades_per_day": wallet.avg_trades_per_day or 0.0,
                "max_drawdown_pct": wallet.max_drawdown_pct or 0.0,
                "total_trades_analyzed": wallet.total_trades_analyzed or 50
            }
            ai_summary, ai_style_tag = await asyncio.wait_for(generate_summary(stats_dict), timeout=2.5)
            if ai_summary:
                wallet.ai_summary = ai_summary
            if ai_style_tag:
                wallet.ai_style_tag = ai_style_tag
            await db.commit()
            await db.refresh(wallet)
        except Exception as e:
            logger.warning(f"Failed or timed out generating summary: {e}")
            win_r = wallet.win_rate_pct or 0.0
            pnl_val = wallet.all_time_pnl_usd or 0.0
            vel = wallet.avg_trades_per_day or 0.0
            if win_r >= 85.0 and vel <= 5.0 and vel > 0:
                wallet.ai_summary = f"Elite low-frequency sniper executing with surgical {win_r:.1f}% accuracy across selective prediction markets. Captures ${pnl_val:,.0f} net alpha with patient, asymmetric positioning and exceptional risk discipline."
                wallet.ai_style_tag = "Surgical Sniper"
            elif win_r >= 80.0:
                wallet.ai_summary = f"High-precision tactical whale maintaining {win_r:.1f}% accuracy with ${pnl_val:,.0f} net realized profit and disciplined drawdown management."
                wallet.ai_style_tag = "High-Conviction Sniper"
            else:
                wallet.ai_summary = f"Systematic market participant with {win_r:.1f}% win rate and ${pnl_val:,.0f} lifetime profit across active Polymarket order books."
                wallet.ai_style_tag = "Alpha Whale"

    # Score Snapshots
    snap_stmt = select(WalletSnapshot).where(
        func.lower(WalletSnapshot.wallet_address) == clean_addr
    ).order_by(WalletSnapshot.snapshot_at.asc()).limit(30)
    snapshots = (await db.execute(snap_stmt)).scalars().all()
    
    score_history = []
    if snapshots:
        score_history = [
            {
                "date": s.snapshot_at.strftime("%Y-%m-%d %H:%M") if getattr(s, "snapshot_at", None) else "Now",
                "score": round(s.baleen_score or 0.0, 1),
                "win_rate": round(s.win_rate_pct or 0.0, 1),
                "pnl": round(s.pnl_usd or 0.0, 2)
            }
            for s in snapshots
        ]
    else:
        # Initial point
        score_history = [
            {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "score": round(wallet.baleen_score or 0.0, 1),
                "win_rate": round(wallet.win_rate_pct or 0.0, 1),
                "pnl": round(wallet.all_time_pnl_usd or 0.0, 2)
            }
        ]
    
    # Fetch recent execution logs for this specific whale
    stmt_trades = select(ExecutionLog).where(
        func.lower(ExecutionLog.source_wallet_address) == clean_addr
    ).order_by(ExecutionLog.executed_at.desc()).limit(20)
    trades = (await db.execute(stmt_trades)).scalars().all()
    
    recent_trades = []
    for t in trades:
        trade_pnl = t.realized_pnl_usd
        if trade_pnl is None and t.status == "FILLED":
            if str(t.id) in _last_known_pnl:
                trade_pnl = _last_known_pnl[str(t.id)]
            else:
                tfp = float(t.user_fill_price or t.whale_entry_price or 0.5)
                tnot = float(t.notional_usd or 0.0)
                tfee = float(t.fee_usd or 0.0)
                tcp = get_live_price(cid=t.market_condition_id or "", outcome=t.resolution_outcome or "Yes", asset=t.onchain_tx_hash or "", fallback=tfp)
                if tfp > 0 and tcp > 0:
                    gp = tnot * ((tcp - tfp) / tfp) if t.side == "BUY" else tnot * ((tfp - tcp) / tfp)
                    trade_pnl = round(gp - tfee, 2)
                else:
                    trade_pnl = round(-tfee, 2)

        recent_trades.append({
            "id": str(t.id),
            "market_question": t.market_question,
            "market_condition_id": t.market_condition_id,
            "side": t.side,
            "outcome": t.resolution_outcome or "Yes",
            "notional_usd": t.notional_usd,
            "fill_price": t.user_fill_price or t.whale_entry_price,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            "status": t.status,
            "pnl_usd": trade_pnl
        })
    
    # Compute daily P&L curve and dual-column wins/losses
    total_pnl = wallet.all_time_pnl_usd or 0.0
    daily_pnl_history = []

    # 1. Use authentic cached on-chain daily PnL curve for the whale's lifetime track record
    if wallet.cached_daily_pnl:
        try:
            cached_pts = json.loads(wallet.cached_daily_pnl)
            if isinstance(cached_pts, list) and len(cached_pts) >= 1:
                # Sanitize legacy synthetic placeholder data (e.g. identical 14272.63 repeating marks)
                first_won = float(cached_pts[0].get("won_usd", 0.0))
                if len(cached_pts) > 10 and abs(first_won - 14272.63) < 0.1:
                    daily_pnl_history = []
                else:
                    daily_pnl_history = cached_pts
        except Exception as e:
            logger.debug(f"Error parsing cached_daily_pnl for {clean_addr}: {e}")
            daily_pnl_history = []

    # 2. If daily_pnl_history is empty, fetch authentic on-chain positions/trades from Polymarket Data API on-demand
    if not daily_pnl_history:
        try:
            from app.discovery.polymarket_client import PolymarketClient
            from app.discovery.scanner import calculate_authentic_wallet_stats
            client = PolymarketClient()
            raw_positions = await client.fetch_wallet_positions(clean_addr)
            raw_activity = await client.fetch_wallet_activity(clean_addr, max_items=4000)
            raw_profile = await client.fetch_wallet_profile(clean_addr)
            raw_trades = await client.fetch_wallet_trades(clean_addr, max_trades=4000)
            raw_closed = await client.fetch_wallet_closed_positions(clean_addr, max_items=4000) if hasattr(client, "fetch_wallet_closed_positions") else []
            await client.close()

            stats = calculate_authentic_wallet_stats(
                address=clean_addr,
                positions=raw_positions,
                activity=raw_activity,
                profile=raw_profile,
                trades=raw_trades,
                closed_positions=raw_closed
            )
            real_hist = stats.get('daily_pnl_history', [])
            if real_hist:
                daily_pnl_history = real_hist
                wallet.cached_daily_pnl = json.dumps(real_hist)
                await db.commit()
        except Exception as e:
            logger.debug(f"Error fetching live on-chain history for {clean_addr}: {e}")

    # 3. Fallback to local DB copied executions only if on-chain history is completely unavailable
    if not daily_pnl_history and trades:
        daily_groups = {}
        for t in sorted(trades, key=lambda x: x.executed_at or datetime.min):
            if not t.executed_at:
                continue
            # Strictly only count fully closed positions with settled realized PnL
            if str(t.status).upper() != "CLOSED" or t.realized_pnl_usd is None:
                continue
            dt_str = t.executed_at.strftime("%Y-%m-%d")
            if dt_str not in daily_groups:
                daily_groups[dt_str] = {"won": 0.0, "lost": 0.0, "count": 0}
            p = float(t.realized_pnl_usd or 0.0)
            if p >= 0:
                daily_groups[dt_str]["won"] += p
            else:
                daily_groups[dt_str]["lost"] += abs(p)
            daily_groups[dt_str]["count"] += 1

        if daily_groups:
            cum = 0.0
            real_history = []
            for d, vals in sorted(daily_groups.items()):
                net = round(vals["won"] - vals["lost"], 2)
                cum += net
                real_history.append({
                    "date": d,
                    "won_usd": round(vals["won"], 2),
                    "lost_usd": round(-abs(vals["lost"]), 2),
                    "net_pnl": net,
                    "daily_pnl": net,
                    "cumulative_pnl": round(cum, 2),
                    "trades_count": vals["count"]
                })
            daily_pnl_history = real_history

    return {
        "wallet": wallet_to_response(wallet),
        "score_history": score_history,
        "daily_pnl_history": daily_pnl_history,
        "recent_trades": recent_trades
    }
