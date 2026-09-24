"""Transparent autonomous paper-roster selection.

This service chooses only from fresh, globally evaluated research candidates.
Intermittent candidates are intentionally returned as standby snipers instead of
being given an idle sleeve. It does not submit orders or grant live approval.
"""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import func, select
from app.models import Wallet, WalletEvidence
from app.sizing.capital_tier import get_target_wallet_count
from app.services.wallet_reset import current_generation
from app.discovery.wallet_evidence import POLICY_VERSION


FRESHNESS = timedelta(hours=24)


def _number(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def _fresh_current(evidence, generation):
    payload = getattr(evidence, 'payload', None) or {}
    return bool(evidence and evidence.observed_at and
                datetime.utcnow() - evidence.observed_at <= FRESHNESS and
                payload.get('generation') == generation and
                payload.get('policy_version') == POLICY_VERSION)


def _summary(wallet, evidence):
    payload = evidence.payload or {}
    metrics = payload.get('metrics') or {}
    return {
        'address': wallet.address,
        'name': wallet.name,
        'pseudonym': wallet.pseudonym,
        'classification': payload.get('classification'),
        'reasons': payload.get('reasons', []),
        'observed_at': evidence.observed_at.isoformat(),
        'all_time_pnl_usd': str(_number(metrics.get('economic_pnl', wallet.all_time_pnl_usd))),
        'realized_pnl_usd': str(_number(metrics.get('realized_pnl'))),
        'recent_pnl_7d': str(_number(metrics.get('trade_pnl_7d'))),
        'recent_pnl_30d': str(_number(metrics.get('trade_pnl_30d'))),
        'fills_per_day_30d': str(_number(metrics.get('fills_per_day_30d'))),
        'active_days_7d': metrics.get('active_days_7d'),
        'closed_position_win_rate_pct': metrics.get('closed_position_win_rate_pct'),
        'closed_position_profit_factor': str(_number(metrics.get('closed_position_profit_factor')))
            if metrics.get('closed_position_profit_factor') is not None else None,
        'positive_pnl_day_rate_30d': metrics.get('positive_pnl_day_rate_30d'),
        'max_curve_drawdown_30d': str(_number(metrics.get('max_curve_drawdown_30d')))
            if metrics.get('max_curve_drawdown_30d') is not None else None,
        'median_inter_fill_gap_hours': metrics.get('median_inter_fill_gap_hours'),
        'evidence_quality_score': metrics.get('evidence_quality_score'),
        'opposing_side_market_ratio_30d': metrics.get('opposing_side_market_ratio_30d'),
        'boundary_buy_ratio_30d': metrics.get('boundary_buy_ratio_30d'),
    }


async def automatic_active_roster(db, capital):
    """Return the capital-appropriate active roster and its auditable reason.

    Ranking is deliberately simple and reproducible: fresh eligible evidence,
    then positive 30-day and 7-day trading P&L, then all-time provider P&L.
    It never promotes an intermittent watchlist wallet into an idle sleeve.
    """
    generation = await current_generation(db)
    rows = (await db.execute(select(Wallet, WalletEvidence).join(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address))).all()
    candidates = []
    for wallet, evidence in rows:
        if wallet.is_hft or not _fresh_current(evidence, generation):
            continue
        payload = evidence.payload or {}
        if payload.get('classification') != 'research_candidate':
            continue
        metrics = payload.get('metrics') or {}
        candidates.append((wallet, evidence, (
            _number(metrics.get('evidence_quality_score')),
            _number(metrics.get('trade_pnl_30d')),
            _number(metrics.get('trade_pnl_7d')),
            _number(metrics.get('economic_pnl', wallet.all_time_pnl_usd)),
            wallet.address,
        )))
    candidates.sort(key=lambda item: item[2], reverse=True)
    target = get_target_wallet_count(capital)
    return [_summary(wallet, evidence) for wallet, evidence, _ in candidates[:target]]


async def active_candidates(db, limit=25):
    """Visible current candidates, independent of the user's capital tier."""
    generation = await current_generation(db)
    rows = (await db.execute(select(Wallet, WalletEvidence).join(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address))).all()
    candidates = []
    for wallet, evidence in rows:
        if wallet.is_hft or not _fresh_current(evidence, generation):
            continue
        if (evidence.payload or {}).get("classification") != "research_candidate":
            continue
        metrics = evidence.payload.get("metrics") or {}
        candidates.append((wallet, evidence, (
            _number(metrics.get("evidence_quality_score")),
            _number(metrics.get("trade_pnl_30d")), _number(metrics.get("trade_pnl_7d")),
            _number(metrics.get("economic_pnl", wallet.all_time_pnl_usd)), wallet.address,
        )))
    candidates.sort(key=lambda item: item[2], reverse=True)
    return [_summary(wallet, evidence) for wallet, evidence, _ in candidates[:limit]]


async def standby_snipers(db):
    """Return visible, fresh intermittent candidates that remain monitored."""
    generation = await current_generation(db)
    rows = (await db.execute(select(Wallet, WalletEvidence).join(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address))).all()
    result = []
    for wallet, evidence in rows:
        if wallet.is_hft or not _fresh_current(evidence, generation):
            continue
        if (evidence.payload or {}).get('classification') == 'watchlist':
            result.append(_summary(wallet, evidence))
    return sorted(result, key=lambda item: (
        Decimal(item['all_time_pnl_usd']), Decimal(item['recent_pnl_30d']), item['address']), reverse=True)


async def roster_evidence_status(db):
    """Return only current evidence counts for the paper-copy dashboard.

    These are intentionally separate from the legacy basket's ``active``
    status, which does not decide automatic paper roster eligibility.
    """
    generation = await current_generation(db)
    rows = (await db.execute(select(Wallet, WalletEvidence).join(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address))).all()
    pending_missing = (await db.execute(select(func.count()).select_from(Wallet).outerjoin(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address).where(
            WalletEvidence.wallet_address.is_(None), Wallet.status == "pending"))).scalar() or 0
    legacy_retained = (await db.execute(select(func.count()).select_from(Wallet).outerjoin(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address).where(
            WalletEvidence.wallet_address.is_(None), Wallet.status != "pending"))).scalar() or 0
    counts = {"active_eligible": 0, "standby": 0, "needs_data": pending_missing,
              "excluded": 0, "stale": 0, "legacy_retained": legacy_retained}
    for wallet, evidence in rows:
        if not _fresh_current(evidence, generation):
            counts["stale"] += 1
            continue
        classification = (evidence.payload or {}).get("classification")
        if classification == "research_candidate" and not wallet.is_hft:
            counts["active_eligible"] += 1
        elif classification == "watchlist" and not wallet.is_hft:
            counts["standby"] += 1
        elif classification == "needs_data":
            counts["needs_data"] += 1
        else:
            counts["excluded"] += 1
    return {"generation": generation, **counts}


async def roster_evidence_registry(db, limit=250):
    """Return inspectable current and stale research decisions for the UI."""
    generation = await current_generation(db)
    rows = (await db.execute(select(Wallet, WalletEvidence).join(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address))).all()
    pending = (await db.execute(select(Wallet).outerjoin(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address).where(
            WalletEvidence.wallet_address.is_(None), Wallet.status == "pending"))).scalars().all()
    rows.extend((wallet, None) for wallet in pending)
    legacy_retained = (await db.execute(select(func.count()).select_from(Wallet).outerjoin(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address).where(
            WalletEvidence.wallet_address.is_(None), Wallet.status != "pending"))).scalar() or 0
    entries = []
    for wallet, evidence in rows:
        payload = (evidence.payload if evidence else None) or {}
        metrics = payload.get("metrics") or {}
        fresh = _fresh_current(evidence, generation)
        classification = payload.get("classification") if fresh else "stale"
        coverage = payload.get("trade_coverage") or {}
        entries.append({
            "address": wallet.address,
            "name": wallet.name,
            "pseudonym": wallet.pseudonym,
            "classification": classification or "stale",
            "fresh": fresh,
            "is_hft": bool(wallet.is_hft),
            "reasons": payload.get("reasons") or (["EVIDENCE_NOT_YET_COLLECTED"] if not evidence else ["STALE_EVIDENCE"]),
            "observed_at": evidence.observed_at.isoformat() if evidence and evidence.observed_at else None,
            "all_time_pnl_usd": str(_number(metrics.get("economic_pnl", wallet.all_time_pnl_usd))),
            "realized_pnl_usd": str(_number(metrics.get("realized_pnl"))),
            "recent_pnl_7d": str(_number(metrics.get("trade_pnl_7d"))),
            "recent_pnl_30d": str(_number(metrics.get("trade_pnl_30d"))),
            "fills_per_day_7d": str(_number(metrics.get("fills_per_day_7d"))),
            "fills_per_day_30d": str(_number(metrics.get("fills_per_day_30d"))),
            "active_days_7d": metrics.get("active_days_7d"),
            "trade_coverage_complete": coverage.get("complete"),
            "trade_coverage_reason": coverage.get("reason"),
            "closed_position_win_rate_pct": metrics.get("closed_position_win_rate_pct"),
            "closed_position_profit_factor": metrics.get("closed_position_profit_factor"),
            "positive_pnl_day_rate_30d": metrics.get("positive_pnl_day_rate_30d"),
            "median_inter_fill_gap_hours": metrics.get("median_inter_fill_gap_hours"),
            "evidence_quality_score": metrics.get("evidence_quality_score"),
        })
    order = {"research_candidate": 0, "watchlist": 1, "needs_data": 2, "stale": 3, "excluded": 4}
    entries.sort(key=lambda row: (order.get(row["classification"], 5), -Decimal(row["recent_pnl_30d"]), row["address"]))
    return {"generation": generation, "total": len(entries), "displayed": min(limit, len(entries)),
            "legacy_retained": legacy_retained, "wallets": entries[:limit]}
