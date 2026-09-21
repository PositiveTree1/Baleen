"""Transparent autonomous paper-roster selection.

This service chooses only from fresh, globally evaluated research candidates.
Intermittent candidates are intentionally returned as standby snipers instead of
being given an idle sleeve. It does not submit orders or grant live approval.
"""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
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
        'recent_pnl_7d': str(_number(metrics.get('trade_pnl_7d'))),
        'recent_pnl_30d': str(_number(metrics.get('trade_pnl_30d'))),
        'fills_per_day_30d': str(_number(metrics.get('fills_per_day_30d'))),
        'active_days_7d': metrics.get('active_days_7d'),
    }


async def automatic_active_roster(db, capital):
    """Return the capital-appropriate active roster and its auditable reason.

    Ranking is deliberately simple and reproducible: fresh eligible evidence,
    then positive 30-day and 7-day trading P&L, then all-time provider P&L.
    It never promotes an intermittent watchlist wallet into an idle sleeve.
    """
    generation = await current_generation(db)
    rows = (await db.execute(select(Wallet, WalletEvidence).outerjoin(
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
            _number(metrics.get('trade_pnl_30d')),
            _number(metrics.get('trade_pnl_7d')),
            _number(metrics.get('economic_pnl', wallet.all_time_pnl_usd)),
            wallet.address,
        )))
    candidates.sort(key=lambda item: item[2], reverse=True)
    target = get_target_wallet_count(capital)
    return [_summary(wallet, evidence) for wallet, evidence, _ in candidates[:target]]


async def standby_snipers(db):
    """Return visible, fresh intermittent candidates that remain monitored."""
    generation = await current_generation(db)
    rows = (await db.execute(select(Wallet, WalletEvidence).outerjoin(
        WalletEvidence, WalletEvidence.wallet_address == Wallet.address))).all()
    result = []
    for wallet, evidence in rows:
        if wallet.is_hft or not _fresh_current(evidence, generation):
            continue
        if (evidence.payload or {}).get('classification') == 'watchlist':
            result.append(_summary(wallet, evidence))
    return sorted(result, key=lambda item: (
        Decimal(item['all_time_pnl_usd']), Decimal(item['recent_pnl_30d']), item['address']), reverse=True)
