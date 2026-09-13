"""Conservative, interpretable screening defaults; not fitted profit forecasts."""
import math
from datetime import datetime, timezone, timedelta


def curve_metrics(stats):
    points = stats.get('daily_pnl_history') or []
    now = datetime.now(timezone.utc)
    recent = [p for p in points if p.get('daily_pnl') is not None and
              datetime.fromisoformat(p['date']) >= now - timedelta(days=90)]
    values = [p['daily_pnl'] for p in recent]
    # Dollar-PnL variability, not a portfolio-return Sharpe (capital is unknown).
    mean = sum(values) / len(values) if values else 0
    sd = math.sqrt(sum((x-mean)**2 for x in values) / len(values)) if values else 0
    stability = mean / sd if sd else (1 if mean > 0 else 0)
    weeks = {}
    for p in recent:
        date = datetime.fromisoformat(p['date']).isocalendar()
        key = (date.year, date.week)
        weeks[key] = weeks.get(key, 0) + p['daily_pnl']
    positive_weeks = sum(v > 0 for v in weeks.values()) / max(1, len(weeks))
    return len(values), sum(values), stability, positive_weeks


def qualify_wallet(stats):
    from app.scoring.engine import ScoringResult
    reason = None
    days, recent_pnl, _, positive_weeks = curve_metrics(stats)
    count = stats.get('resolved_positions_count', 0)
    if not stats.get('history_verified') or not stats.get('profile_verified') or not stats.get('settled_data_complete', True):
        reason = 'UNVERIFIED_PERFORMANCE_DATA'
    elif count < 30 or days < 60:
        reason = 'INSUFFICIENT_OBSERVED_HISTORY'
    elif stats.get('is_inactive_7d') or stats.get('is_hft') or stats.get('is_wash_trading'):
        reason = 'RECENCY_OR_COPYABILITY_FAILED'
    elif stats.get('all_time_pnl_usd', 0) <= 0 or recent_pnl <= 0 or stats.get('cumulative_pnl', 1) <= 0:
        reason = 'NON_POSITIVE_RECENT_OR_LIFETIME_PNL'
    elif stats.get('expectancy_usd', 0) <= 0 or (stats.get('profit_factor') is not None and stats['profit_factor'] < 1.25):
        reason = 'INSUFFICIENT_PAYOFF_AFTER_LOSSES'
    elif stats.get('max_drawdown_pct', 100) > 25:
        reason = 'PNL_DRAWDOWN_EXCEEDED'
    elif positive_weeks < 0.55 or stats.get('outlier_concentration_pct', 1) > 0.35:
        reason = 'PROFIT_TOO_CONCENTRATED'
    elif stats.get('unrealized_open_pnl', 0) < -0.25 * stats.get('all_time_pnl_usd', 0):
        reason = 'OPEN_POSITION_LOSSES_EXCEEDED'
    if reason:
        return ScoringResult('rejected', None, reason, False)
    score = quality_score(stats)
    return ScoringResult('active', 'gold_sniper' if score >= 75 else 'standard', None, True)


def quality_score(stats):
    if not stats.get('history_verified'):
        return 0.0
    _, _, stability, positive_weeks = curve_metrics(stats)
    pf = stats.get('profit_factor')
    # No observed losses is undefined PF, not infinite certainty.
    payoff = min(1, max(0, (pf - 1) / 2)) if pf is not None else 0.5
    confidence = min(1, stats.get('resolved_positions_count', 0) / 200)
    loss_control = max(0, 1 - stats.get('max_drawdown_pct', 100) / 25)
    breadth = max(0, 1 - stats.get('outlier_concentration_pct', 1))
    score = (25 * payoff + 20 * positive_weeks + 15 * min(1, max(0, stability) / 0.5)
             + 15 * loss_control + 15 * confidence + 10 * breadth)
    return round(score, 1)
