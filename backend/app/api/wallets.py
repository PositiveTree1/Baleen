import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.analysis.ai_summary import generate_summary
from app.database import get_db
from app.auth import get_current_user_optional
from app.models import ExecutionLog, Wallet, WalletSnapshot, User, WalletEvidence
from app.services.mark_to_market import _last_known_pnl, get_live_price
from app.services.polymarket_fees import calculate_polymarket_fee

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wallets", tags=["wallets"])

def wallet_to_response(w: Wallet, evidence: WalletEvidence | None = None) -> dict:
    payload = evidence.payload if evidence and isinstance(evidence.payload, dict) else {}
    metrics = payload.get("metrics") or {}
    verified = bool(evidence and payload.get("classification") in {"research_candidate", "watchlist", "needs_data", "excluded"})
    classification = payload.get("classification")
    response = {
        "address": w.address,
        "name": w.name,
        "pseudonym": w.pseudonym,
        "profileImage": w.profile_image,
        "tier": "gold_sniper" if classification == "watchlist" else (w.tier or "standard"),
        "win_rate_pct": metrics.get("closed_position_win_rate_pct") if verified else w.win_rate_pct,
        "wilson_lb": getattr(w, "wilson_lb", None),
        "all_time_pnl_usd": metrics.get("economic_pnl", w.all_time_pnl_usd) if verified else w.all_time_pnl_usd,
        "avg_trades_per_day": metrics.get("fills_per_day_30d") if verified else w.avg_trades_per_day,
        "trades_per_hour": getattr(w, "trades_per_hour", None),
        "baleen_score": metrics.get("evidence_quality_score") if verified else w.baleen_score,
        "ai_style_tag": w.ai_style_tag,
        "ai_summary": w.ai_summary,
        "max_drawdown_pct": w.max_drawdown_pct,
        "outlier_concentration_pct": w.outlier_concentration_pct,
        "alpha_per_trade": getattr(w, "alpha_per_trade", None),
        "profit_factor": metrics.get("closed_position_profit_factor") if verified else getattr(w, "profit_factor", None),
        "status": classification or w.status or "active",
        "dormant": bool(w.dormant),
        "is_hft": bool(getattr(w, "is_hft", False)),
        "first_trade_at": w.first_trade_at.isoformat() if getattr(w, "first_trade_at", None) else None,
        "last_trade_at": w.last_trade_at.isoformat() if getattr(w, "last_trade_at", None) else None,
        "total_trades_analyzed": w.total_trades_analyzed,
        "avg_hold_hours": None,  # Trade spacing is not position holding duration.
        "median_inter_trade_gap_hours": metrics.get("median_inter_fill_gap_hours") if verified else getattr(w, "median_inter_trade_gap_hours", None),
        "rejection_reason": "; ".join(payload.get("reasons", [])) if verified else w.rejection_reason,
        "first_seen_at": w.first_seen_at.isoformat() if w.first_seen_at else None,
        "last_scored_at": w.last_scored_at.isoformat() if w.last_scored_at else None,
    }
    return response

@router.get("")
async def list_wallets(
    response: Response,
    tier: Optional[str] = None,
    dormant: Optional[bool] = None,
    status: Optional[str] = None,
    limit: int = 150,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    from app.services.wallet_reset import current_generation
    generation = await current_generation(db)
    response.headers["X-Wallet-Generation"] = generation
    response.headers["Cache-Control"] = "no-store"
    current_only = not status and dormant is None and not tier
    stmt = select(Wallet, WalletEvidence).join(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address
    ).where(Wallet.is_hft == False) if current_only else select(Wallet).where(Wallet.is_hft == False)
    
    if status:
        stmt = stmt.where(Wallet.status == status)
    elif dormant is not None:
        stmt = stmt.where(Wallet.status == "active", Wallet.dormant == dormant)
    elif tier:
        stmt = stmt.where(Wallet.status == "active", Wallet.tier == tier, Wallet.dormant == False)
    if current_only:
        # Keep the public dashboard list portable across PostgreSQL/Supabase
        # JSON implementations. Filtering this small, evidence-only set in
        # Python also prevents a malformed legacy JSON payload from turning
        # the whole wallet list into an HTTP 500.
        from app.discovery.wallet_evidence import POLICY_VERSION
        freshness_cutoff = datetime.utcnow() - timedelta(hours=24)
        rows = []
        for wallet, evidence in (await db.execute(stmt)).all():
            payload = evidence.payload if isinstance(evidence.payload, dict) else {}
            if (evidence.observed_at < freshness_cutoff
                    or payload.get('generation') != generation
                    or payload.get('policy_version') != POLICY_VERSION
                    or payload.get('classification') != 'research_candidate'):
                continue
            metrics = payload.get('metrics') if isinstance(payload.get('metrics'), dict) else {}
            rows.append((wallet, evidence, metrics))
        rows.sort(key=lambda row: (
            row[2].get('evidence_quality_score') is not None,
            row[2].get('evidence_quality_score') or float('-inf'),
            row[2].get('economic_pnl') or row[0].all_time_pnl_usd or float('-inf'),
            row[0].address,
        ), reverse=True)
        return [wallet_to_response(wallet, evidence) for wallet, evidence, _ in rows[offset:offset + limit]]

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

@router.get("/{address}/research")
async def get_wallet_research(address: str, db: AsyncSession = Depends(get_db)):
    import re
    from app.discovery.polymarket_client import PolymarketClient
    from app.discovery.wallet_evidence import collect_evidence
    from app.models import WalletEvidence
    clean = address.lower().strip()
    if not re.fullmatch(r"0x[0-9a-f]{40}", clean):
        raise HTTPException(status_code=422, detail="Invalid wallet address")
    cached = await db.get(WalletEvidence, clean)
    if cached and datetime.utcnow() - cached.observed_at < timedelta(hours=24):
        return cached.payload
    client = PolymarketClient()
    try:
        return await asyncio.wait_for(collect_evidence(client, clean), timeout=45)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Wallet evidence collection timed out; retry later")
    finally:
        await client.close()


@router.get("/{address}")
async def get_wallet(address: str, response: Response, db: AsyncSession = Depends(get_db)):
    from app.services.wallet_reset import current_generation
    response.headers["X-Wallet-Generation"] = await current_generation(db)
    response.headers["Cache-Control"] = "no-store"
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
                from app.discovery.wallet_evidence import finite
                p_pnl = finite(prof.get("pnl")) if isinstance(prof, dict) and prof.get("reported_period") == "ALL" else None
                if p_pnl is None or p_pnl < 50000:
                    raise HTTPException(status_code=404, detail="Wallet is not in the qualified research registry")

                wallet = Wallet(
                    address=clean_addr,
                    name=p_name,
                    pseudonym=p_pseudo,
                    profile_image=p_img,
                    all_time_pnl_usd=None,  # Threshold proof is not the V2 account curve.
                    win_rate_pct=None,
                    baleen_score=None,
                    status="tracked",
                    tier="standard",
                    dormant=False,
                    is_hft=False,
                    avg_trades_per_day=None,
                    total_trades_analyzed=None
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
                    # Profile metadata cannot overwrite V2 P&L or advance the
                    # research evaluation timestamp after a statistics reset.
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
    if (not wallet.ai_summary or not wallet.ai_style_tag or is_corrupted) and all(
        v is not None for v in (wallet.win_rate_pct, wallet.all_time_pnl_usd, wallet.avg_trades_per_day, wallet.max_drawdown_pct)
    ):
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

    evidence = await db.get(WalletEvidence, clean_addr)

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
    evidence_score = ((evidence.payload.get("metrics") or {}).get("evidence_quality_score")
                      if evidence else None)
    if evidence_score is not None:
        score_history.append({
            "date": evidence.observed_at.strftime("%Y-%m-%d %H:%M"),
            "score": round(float(evidence_score), 1),
            "win_rate": (evidence.payload.get("metrics") or {}).get("closed_position_win_rate_pct"),
            "pnl": (evidence.payload.get("metrics") or {}).get("economic_pnl"),
        })
    
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
    
    # Provider economic P&L is a marked account series, not a sequence of
    # realized wins/losses. Never substitute partial closed-position history.
    from app.discovery.wallet_evidence import pnl_series, chart_history
    daily_pnl_history = evidence.payload.get("daily_pnl_history", []) if evidence else []
    series = None
    curve_status = "cached" if daily_pnl_history else "unavailable"
    # A selected wallet already has a verified provider curve in its evidence
    # record.  Do not make the drawer wait on another external API request.
    if not daily_pnl_history:
        client = PolymarketClient()
        try:
            series = await asyncio.wait_for(pnl_series(client, clean_addr), timeout=8.0)
        except Exception as exc:
            logger.debug("Wallet series unavailable: %s", exc)
        finally:
            await client.close()
        daily_pnl_history = chart_history(series)
        curve_status = "observed" if daily_pnl_history else "unavailable"
    response_wallet = wallet_to_response(wallet, evidence)
    if daily_pnl_history:
        response_wallet["all_time_pnl_usd"] = daily_pnl_history[-1]["cumulative_pnl"]
    # Legacy drawdown was calculated on cumulative profits, not equity.
    response_wallet["max_drawdown_pct"] = None

    return {
        "wallet": response_wallet,
        "pnl_metadata": {"metric": "economic_pnl", "source": "polymarket_v2", "status": curve_status, "source_fidelity": series.get("source_fidelity") if series else None},
        "research": evidence.payload if evidence else None,
        "score_history": score_history,
        "daily_pnl_history": daily_pnl_history,
        "recent_trades": recent_trades
    }
