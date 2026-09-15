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
from app.auth import get_current_user_optional
from app.models import ExecutionLog, Wallet, WalletSnapshot, User
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
        "win_rate_pct": w.win_rate_pct,
        "wilson_lb": getattr(w, "wilson_lb", None),
        "all_time_pnl_usd": w.all_time_pnl_usd,
        "avg_trades_per_day": w.avg_trades_per_day,
        "trades_per_hour": getattr(w, "trades_per_hour", None),
        "baleen_score": w.baleen_score,
        "ai_style_tag": w.ai_style_tag,
        "ai_summary": w.ai_summary,
        "max_drawdown_pct": w.max_drawdown_pct,
        "outlier_concentration_pct": w.outlier_concentration_pct,
        "alpha_per_trade": getattr(w, "alpha_per_trade", None),
        "profit_factor": getattr(w, "profit_factor", None),
        "status": w.status or "active",
        "dormant": bool(w.dormant),
        "is_hft": bool(getattr(w, "is_hft", False)),
        "first_trade_at": w.first_trade_at.isoformat() if getattr(w, "first_trade_at", None) else None,
        "last_trade_at": w.last_trade_at.isoformat() if getattr(w, "last_trade_at", None) else None,
        "total_trades_analyzed": w.total_trades_analyzed,
        "avg_hold_hours": None,  # Trade spacing is not position holding duration.
        "median_inter_trade_gap_hours": getattr(w, "median_inter_trade_gap_hours", None),
        "rejection_reason": w.rejection_reason,
        "first_seen_at": w.first_seen_at.isoformat() if w.first_seen_at else None,
        "last_scored_at": w.last_scored_at.isoformat() if w.last_scored_at else None,
    }

@router.get("")
async def list_wallets(
    tier: Optional[str] = None,
    dormant: Optional[bool] = None,
    status: Optional[str] = None,
    limit: int = 150,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Wallet).where(Wallet.is_hft == False)
    
    if status:
        stmt = stmt.where(Wallet.status == status)
    elif dormant is not None:
        stmt = stmt.where(Wallet.status == "active", Wallet.dormant == dormant)
    elif tier:
        stmt = stmt.where(Wallet.status == "active", Wallet.tier == tier, Wallet.dormant == False)
    else:
        # Default roster: show active and tracked wallets that have been scored and have authentic PnL
        stmt = stmt.where(
            Wallet.status.in_(["active", "tracked"]),
            Wallet.all_time_pnl_usd.is_not(None)
        )
        
    stmt = stmt.order_by(Wallet.baleen_score.desc().nullslast(), Wallet.all_time_pnl_usd.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [wallet_to_response(w) for w in result.scalars().all()]

@router.get("/copied-stats")
async def get_copied_wallet_stats(
    user_id: Optional[str] = Query(None, alias="userId"),
    userId: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    current_user = current_user if isinstance(current_user, User) else None
    from uuid import UUID

    stmt = select(ExecutionLog).where(ExecutionLog.is_sandbox.is_(True), ExecutionLog.side == "BUY", ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]))
    eff_user_id = None
    if isinstance(user_id, (str, UUID)):
        eff_user_id = str(user_id).strip()
    elif isinstance(userId, (str, UUID)):
        eff_user_id = str(userId).strip()

    if eff_user_id:
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required to view private copied wallet statistics."
            )
        try:
            u_uuid = UUID(eff_user_id)
        except Exception:
            raise HTTPException(status_code=404, detail="User not found")
        is_admin = getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"
        if str(current_user.id) != str(u_uuid) and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot view another user's copied wallet statistics."
            )
        stmt_user = stmt.where(ExecutionLog.user_id == u_uuid)
        logs = (await db.execute(stmt_user)).scalars().all()
    elif current_user:
        stmt_user = stmt.where(ExecutionLog.user_id == current_user.id)
        logs = (await db.execute(stmt_user)).scalars().all()
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
                "unvalued": 0,
                "wins": 0,
                "losses": 0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
            }
        
        from app.services.execution_valuation import execution_valuation, finite
        notional = finite(log.notional_usd)
        stats = wallet_stats[addr]
        stats["trades_copied"] += 1
        stats["total_notional"] = (stats["total_notional"] + notional
            if stats["total_notional"] is not None and notional is not None else None)
        pnl = execution_valuation(log)['pnl']
        if pnl is None:
            stats['unvalued'] += 1
            continue
        stats['net_pnl'] += pnl
        if log.status in ('CLOSED', 'RESOLVED'):
            if pnl > 0:
                stats['wins'] += 1
                stats['gross_profit'] += pnl
            elif pnl < 0:
                stats['losses'] += 1
                stats['gross_loss'] += abs(pnl)

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
        wr = (stats["wins"] / total_resolved * 100.0) if total_resolved > 0 else None
        pf = (stats["gross_profit"] / stats["gross_loss"]) if stats["gross_loss"] > 0 else None
        roi = (stats["net_pnl"] / stats["total_notional"] * 100.0) if stats["total_notional"] and not stats["unvalued"] else None

        disp_name = (w_obj.name if w_obj and w_obj.name else (w_obj.pseudonym if w_obj and w_obj.pseudonym else None))
        copy_rate = None  # No complete eligible-source denominator is recorded here.

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
            "totalNotional": round(stats["total_notional"], 2) if stats["total_notional"] is not None else None,
            "netPnl": round(stats["net_pnl"], 2) if not stats["unvalued"] else None,
            "knownPnlUsd": round(stats["net_pnl"], 2),
            "unvaluedTradesCount": stats["unvalued"],
            "mirroredPnl": round(stats["net_pnl"], 2) if not stats["unvalued"] else None,
            "roiPct": round(roi, 2) if roi is not None else None,
            "winRateCopied": round(wr, 1) if wr is not None else None,
            "profitFactor": round(pf, 2) if pf is not None else None,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "copyRatePct": copy_rate,
        })

    results.sort(key=lambda r: (r["netPnl"] is not None, r["netPnl"] or 0), reverse=True)
    return results

@router.get("/{address}")
async def get_wallet(address: str, db: AsyncSession = Depends(get_db)):
    clean_addr = address.lower().strip()
    
    # Wallet query (case insensitive)
    stmt = select(Wallet).where(func.lower(Wallet.address) == clean_addr)
    wallet = (await db.execute(stmt)).scalar_one_or_none()
    
    # Auto-discover wallet on-demand if it's a valid address but not yet in database
    is_new = False
    from app.discovery.polymarket_client import PolymarketClient
    client = PolymarketClient()
    try:
        if not wallet:
            if len(clean_addr) == 42 and clean_addr.startswith("0x"):
                try:
                    prof = await asyncio.wait_for(client.fetch_wallet_profile(clean_addr), timeout=3.5)
                except Exception:
                    prof = None

                p_name = (prof.get("name") or prof.get("userName")) if isinstance(prof, dict) else None
                p_pseudo = prof.get("pseudonym") if isinstance(prof, dict) else None
                p_img = prof.get("profileImage") if isinstance(prof, dict) else None
                p_pnl = round(float(prof.get("pnl") or prof.get("profit") or 0.0), 2) if isinstance(prof, dict) else 0.0

                wallet = Wallet(
                    address=clean_addr,
                    name=p_name,
                    pseudonym=p_pseudo,
                    profile_image=p_img,
                    all_time_pnl_usd=p_pnl,
                    win_rate_pct=60.0,
                    baleen_score=70.0,
                    status="tracked",
                    tier="standard",
                    dormant=False,
                    is_hft=False,
                    avg_trades_per_day=5.0,
                    total_trades_analyzed=50
                )
                db.add(wallet)
                await db.commit()
                await db.refresh(wallet)
                is_new = True
            else:
                raise HTTPException(status_code=404, detail="Wallet not found")

        # On-demand refresh of profile metadata if missing or stale (> 30 mins)
        now_utc = datetime.utcnow()
        is_stale = (
            not wallet.name
            or not wallet.profile_image
            or wallet.all_time_pnl_usd is None
            or not wallet.last_scored_at
            or (now_utc - wallet.last_scored_at).total_seconds() > 1800
        )
        if not is_new and is_stale:
            try:
                profile = await asyncio.wait_for(client.fetch_wallet_profile(clean_addr), timeout=2.5)
                if profile and isinstance(profile, dict):
                    p_name = profile.get("name") or profile.get("userName")
                    p_pseudo = profile.get("pseudonym")
                    p_img = profile.get("profileImage")
                    p_pnl = profile.get("pnl") if profile.get("pnl") is not None else profile.get("profit")
                    
                    updated = False
                    if p_name and wallet.name != p_name:
                        wallet.name = str(p_name)
                        updated = True
                    if p_pseudo and wallet.pseudonym != p_pseudo:
                        wallet.pseudonym = str(p_pseudo)
                        updated = True
                    if p_img and wallet.profile_image != p_img:
                        wallet.profile_image = str(p_img)
                        updated = True
                    if p_pnl is not None:
                        try:
                            pnl_val = round(float(p_pnl), 2)
                            if abs((wallet.all_time_pnl_usd or 0.0) - pnl_val) > 0.01:
                                wallet.all_time_pnl_usd = pnl_val
                                updated = True
                        except (ValueError, TypeError):
                            pass
                    wallet.last_scored_at = now_utc
                    if updated:
                        await db.commit()
                        await db.refresh(wallet)
            except Exception as e:
                logger.debug(f"Profile refresh note for {clean_addr}: {e}")
    finally:
        await client.close()

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
                "total_trades_analyzed": wallet.total_trades_analyzed
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
            wallet.ai_summary = None
            wallet.ai_style_tag = None

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
    
    # Fetch recent execution logs for this specific whale
    stmt_trades = select(ExecutionLog).where(
        func.lower(ExecutionLog.source_wallet_address) == clean_addr,
        ExecutionLog.user_id.is_(None),
        ExecutionLog.is_sandbox.is_(True),
    ).order_by(ExecutionLog.executed_at.desc()).limit(20)
    trades = (await db.execute(stmt_trades)).scalars().all()
    
    recent_trades = []
    for t in trades:
        from app.services.execution_valuation import execution_valuation
        trade_pnl = execution_valuation(t)['pnl']

        recent_trades.append({
            "id": str(t.id),
            "market_question": t.market_question,
            "market_condition_id": t.market_condition_id,
            "side": t.side,
            "outcome": t.resolution_outcome or "Yes",
            "notional_usd": t.notional_usd,
            "fill_price": t.user_fill_price,
            "execution_mode": "paper",
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            "status": t.status,
            "pnl_usd": trade_pnl
        })
    
    # Compute daily P&L curve and dual-column wins/losses
    total_pnl = wallet.all_time_pnl_usd or 0.0
    daily_pnl_history = []

    # 1. Primary: Query Polymarket authentic timeseries and user-stats directly
    client = PolymarketClient()
    try:
        raw_pts = []
        user_stats = None
        try:
            pnl_task = client.fetch_wallet_pnl_timeseries(clean_addr, interval="all", fidelity="1d")
            stats_task = client.fetch_wallet_user_stats(clean_addr)
            pnl_res, stats_res = await asyncio.wait_for(
                asyncio.gather(pnl_task, stats_task, return_exceptions=True),
                timeout=4.0
            )
            raw_pts = pnl_res if isinstance(pnl_res, list) else []
            user_stats = stats_res if isinstance(stats_res, dict) else None
        except Exception as e:
            logger.debug(f"Polymarket user-pnl/stats fetch note for {clean_addr}: {e}")

        if raw_pts:
            date_map = {}
            for pt in raw_pts:
                if isinstance(pt, dict) and "t" in pt and "p" in pt:
                    try:
                        dt = datetime.utcfromtimestamp(pt["t"]).strftime("%Y-%m-%d")
                        date_map[dt] = float(pt["p"])
                    except Exception:
                        pass

            if date_map:
                pts_history = []
                prev_p = 0.0
                for i, dt in enumerate(sorted(date_map.keys())):
                    cum = round(date_map[dt], 2)
                    daily = round(cum - prev_p if i > 0 else cum, 2)
                    prev_p = cum
                    pts_history.append({
                        "date": dt,
                        "won_usd": max(0.0, daily),
                        "lost_usd": -abs(daily) if daily < 0 else 0.0,
                        "net_pnl": daily,
                        "daily_pnl": daily,
                        "cumulative_pnl": cum,
                        "trades_count": 1
                    })

                if pts_history:
                    daily_pnl_history = pts_history
                    wallet.cached_daily_pnl = json.dumps(pts_history)
                    latest_pnl = round(pts_history[-1]["cumulative_pnl"], 2)
                    wallet.all_time_pnl_usd = latest_pnl

        if user_stats:
            trades_cnt = user_stats.get("trades") or (user_stats.get("all_time_pnl") or {}).get("trade_count")
            if trades_cnt:
                try:
                    wallet.total_trades_analyzed = int(trades_cnt)
                except (ValueError, TypeError):
                    pass

        if raw_pts or user_stats:
            await db.commit()
            await db.refresh(wallet)
    except Exception as e:
        logger.debug(f"Error querying Polymarket user-pnl for {clean_addr}: {e}")
    finally:
        await client.close()

    # 2. Secondary: Fallback to existing cached on-chain daily PnL curve if user-pnl returned empty
    if not daily_pnl_history and wallet.cached_daily_pnl:
        try:
            cached_pts = json.loads(wallet.cached_daily_pnl)
            if isinstance(cached_pts, list) and len(cached_pts) >= 1:
                first_won = float(cached_pts[0].get("won_usd", 0.0))
                if len(cached_pts) > 10 and abs(first_won - 14272.63) < 0.1:
                    daily_pnl_history = []
                elif len(cached_pts) < 15 and getattr(wallet, 'total_trades_analyzed', 0) and (wallet.total_trades_analyzed or 0) > 30:
                    daily_pnl_history = []
                else:
                    daily_pnl_history = cached_pts
        except Exception as e:
            logger.debug(f"Error parsing cached_daily_pnl for {clean_addr}: {e}")
            daily_pnl_history = []

    # 3. Tertiary: Fallback to multi-page closed positions & activity scanner reconstruction
    if not daily_pnl_history:
        client = PolymarketClient()
        try:
            async def _fetch_deep_history():
                cp_desc = [
                    client._fetch_with_retry(
                        f"{client.data_api_url}/closed-positions",
                        params={"user": clean_addr, "limit": 50, "offset": i * 50, "sortBy": "timestamp", "sortDirection": "DESC"}
                    )
                    for i in range(25)
                ]
                cp_asc = [
                    client._fetch_with_retry(
                        f"{client.data_api_url}/closed-positions",
                        params={"user": clean_addr, "limit": 50, "offset": i * 50, "sortBy": "timestamp", "sortDirection": "ASC"}
                    )
                    for i in range(15)
                ]
                tr_tasks = [
                    client._fetch_with_retry(
                        f"{client.data_api_url}/trades",
                        params={"user": clean_addr, "limit": 500, "offset": i * 500}
                    )
                    for i in range(4)
                ]
                act_tasks = [
                    client._fetch_with_retry(
                        f"{client.data_api_url}/activity",
                        params={"user": clean_addr, "limit": 500, "offset": i * 500, "sortBy": "TIMESTAMP", "sortDirection": "DESC"}
                    )
                    for i in range(4)
                ]
                pos_task = client.fetch_wallet_positions(clean_addr)
                prof_task = client.fetch_wallet_profile(clean_addr)

                all_results = await asyncio.gather(
                    *cp_desc, *cp_asc, *tr_tasks, *act_tasks, pos_task, prof_task,
                    return_exceptions=True
                )
                
                # Extract closed positions with deduplication
                closed_positions = []
                seen_cp = set()
                for r in all_results[:40]:
                    if isinstance(r, list):
                        for item in r:
                            if isinstance(item, dict):
                                k = (str(item.get("conditionId") or ""), str(item.get("asset") or ""), str(item.get("timestamp") or ""))
                                if k not in seen_cp:
                                    seen_cp.add(k)
                                    closed_positions.append(item)

                # Extract trades
                trades = []
                for r in all_results[40:44]:
                    if isinstance(r, list):
                        trades.extend([t for t in r if isinstance(t, dict)])

                # Extract activity
                activity = []
                for r in all_results[44:48]:
                    if isinstance(r, list):
                        activity.extend([a for a in r if isinstance(a, dict)])

                positions = all_results[48] if isinstance(all_results[48], list) else []
                profile = all_results[49] if isinstance(all_results[49], dict) else {"pnl": total_pnl, "vol": getattr(wallet, "volume_usd", 0.0)}

                return closed_positions, trades, activity, positions, profile

            closed_positions, trades, activity, positions, profile = await asyncio.wait_for(
                _fetch_deep_history(),
                timeout=8.0
            )

            if closed_positions or trades or positions or activity:
                from app.discovery.scanner import calculate_authentic_wallet_stats
                stats = calculate_authentic_wallet_stats(
                    address=clean_addr,
                    positions=positions,
                    activity=activity,
                    profile=profile,
                    trades=trades,
                    closed_positions=closed_positions
                )
                real_hist = stats.get('daily_pnl_history', [])
                if real_hist:
                    daily_pnl_history = real_hist
                    wallet.cached_daily_pnl = json.dumps(real_hist)

                if stats:
                    if stats.get('all_time_pnl_usd') is not None and (wallet.all_time_pnl_usd is None or wallet.all_time_pnl_usd == 0):
                        wallet.all_time_pnl_usd = round(float(stats['all_time_pnl_usd']), 2)
                    if stats.get('win_rate_pct') is not None and wallet.win_rate_pct is None:
                        wallet.win_rate_pct = round(float(stats['win_rate_pct']), 1)
                    if stats.get('total_trades_analyzed') is not None and not wallet.total_trades_analyzed:
                        wallet.total_trades_analyzed = int(stats['total_trades_analyzed'])
                    if stats.get('max_drawdown_pct') is not None and wallet.max_drawdown_pct is None:
                        wallet.max_drawdown_pct = round(float(stats['max_drawdown_pct']), 1)
                    if stats.get('baleen_score') is not None and wallet.baleen_score is None:
                        wallet.baleen_score = round(float(stats['baleen_score']), 1)

                await db.commit()
                await db.refresh(wallet)
        except Exception as e:
            logger.debug(f"Error computing deep live on-chain history for {clean_addr}: {e}")
        finally:
            await client.close()

    # Missing source history stays unavailable. Follower paper performance
    # cannot substitute for the source wallet's on-chain performance.

    return {
        "wallet": wallet_to_response(wallet),
        "score_history": score_history,
        "daily_pnl_history": daily_pnl_history,
        "recent_trades": recent_trades
    }
