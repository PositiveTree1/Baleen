import math
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Wallet
from app.scoring.engine import score_wallet

logger = logging.getLogger(__name__)

def compute_raw_factors(stats: dict) -> dict:
    """
    Computes raw metrics across closed positions for candidate pool normalization:
    1. Odds-Weighted Win Rate Edge: Win Rate - avgPrice (30% weight)
    2. Risk-Adjusted Sharpe Ratio: mean(pct_pnl) / stdev(pct_pnl) (30% weight)
    3. Recency-Weighted EMA: 30-day half-life EMA over closed PnL (20% weight)
    4. Category Consistency: Count of profitable distinct categories (10% weight)
    5. Copyability Penalty: Trade size relative to typical depth (10% weight subtracted)
    """
    win_rate = float(stats.get('win_rate_pct', 0) or 0)
    avg_price = float(stats.get('avg_entry_price', 0.50) or 0.50)
    pnl = float(stats.get('all_time_pnl_usd', 0) or 0)
    daily_history = stats.get('daily_pnl_history') or []
    category_count = int(stats.get('category_count', 3) or 3)
    median_trade_size = float(stats.get('median_trade_size', 150.0) or 150.0)

    # 1. Odds-Weighted Edge: Win Rate % minus implied price probability
    # e.g., 60% win rate at 0.55 entry price has +0.05 edge
    implied_prob = max(0.05, min(0.95, avg_price))
    actual_prob = win_rate / 100.0
    odds_edge = actual_prob - implied_prob

    # 2. Risk-Adjusted Return (Sharpe on trade series / daily history)
    if daily_history and len(daily_history) >= 5:
        nets = [float(h.get('net_pnl') or h.get('daily_pnl') or 0.0) for h in daily_history]
        mean_pnl = sum(nets) / len(nets)
        variance = sum((n - mean_pnl)**2 for n in nets) / len(nets)
        stdev = math.sqrt(variance)
        sharpe_raw = mean_pnl / (stdev + 1e-6) if stdev > 0 else 1.0
    else:
        sharpe_raw = 1.0

    # 3. Recency-Weighted EMA (30-day half-life decay)
    recency_ema = float(stats.get('recency_ema', 0.0) or 0.0)
    if recency_ema == 0.0 and daily_history:
        alpha_30d = 1.0 - math.exp(-math.log(2) / 30.0)
        for h in daily_history:
            net_d = float(h.get("daily_pnl") or 0.0)
            recency_ema = (1.0 - alpha_30d) * recency_ema + alpha_30d * net_d
    elif recency_ema == 0.0:
        recency_ema = pnl / 30.0

    # 4. Category Consistency: Count of profitable categories
    cat_raw = float(category_count)

    # 5. Copyability Penalty: Larger trades relative to typical market depth incur higher penalty
    # Typical liquidity depth ~ $5,000; median_trade_size / 5,000
    copy_penalty_raw = min(1.0, median_trade_size / 5000.0)

    return {
        "odds_edge": odds_edge,
        "sharpe": sharpe_raw,
        "recency_ema": recency_ema,
        "category_count": cat_raw,
        "copy_penalty": copy_penalty_raw
    }

def normalize_and_score_pool(candidate_stats_list: List[dict]) -> List[float]:
    """
    5-Factor Composite Scoring across Candidate Pool:
    Calibrated benchmark scoring ensuring scores reflect genuine hedge-fund quantitative performance (0 - 100 scale):
    - Odds-Weighted Win Rate Edge: 30% weight (benchmark +25% edge = 100 pts)
    - Risk-Adjusted Sharpe Ratio: 30% weight (benchmark 2.5 Sharpe = 100 pts)
    - Recency-Weighted PnL EMA: 20% weight (log-scaled benchmark $10k/day = 100 pts)
    - Category Consistency: 10% weight (3+ distinct categories = 100 pts)
    - Copyability Penalty: -10% weight subtracted for trade sizes exceeding liquidity
    """
    if not candidate_stats_list:
        return []

    raw_factors_list = [compute_raw_factors(s) for s in candidate_stats_list]
    final_scores = []

    for rf in raw_factors_list:
        # 1. Odds Edge: -0.10 to +0.25 mapped to 0 - 100
        norm_odds = max(0.0, min(100.0, ((rf["odds_edge"] + 0.10) / 0.35) * 100.0))

        # 2. Risk-adjusted Sharpe: 0.0 to 2.5 mapped to 0 - 100
        norm_sharpe = max(0.0, min(100.0, (rf["sharpe"] / 2.5) * 100.0))

        # 3. Recency EMA: Logarithmic scaling ($10 to $10,000/day mapped to 0 - 100)
        norm_recency = max(0.0, min(100.0, (math.log10(max(10.0, rf["recency_ema"])) / 4.0) * 100.0))

        # 4. Category count: 1 to 3+ categories mapped to 33 - 100
        norm_cat = max(0.0, min(100.0, (rf["category_count"] / 3.0) * 100.0))

        # 5. Copyability Penalty (0 to 10 points subtracted)
        copy_penalty = min(1.0, rf["copy_penalty"]) * 10.0

        # Weighted composite
        composite = (
            (0.30 * norm_odds) +
            (0.30 * norm_sharpe) +
            (0.20 * norm_recency) +
            (0.10 * norm_cat) -
            copy_penalty
        )
        scaled_score = round(max(0.0, min(100.0, composite)), 1)
        final_scores.append(scaled_score)

    return final_scores

def compute_baleen_score(stats: dict) -> float:
    """Computes standalone Baleen Score for a single wallet."""
    raw = compute_raw_factors(stats)
    norm_odds = max(0.0, min(100.0, ((raw["odds_edge"] + 0.10) / 0.35) * 100.0))
    norm_sharpe = max(0.0, min(100.0, (raw["sharpe"] / 2.5) * 100.0))
    norm_recency = max(0.0, min(100.0, (math.log10(max(10.0, raw["recency_ema"])) / 4.0) * 100.0))
    norm_cat = max(0.0, min(100.0, (raw["category_count"] / 3.0) * 100.0))
    copy_penalty = min(1.0, raw["copy_penalty"]) * 10.0

    composite = (
        (0.30 * norm_odds) +
        (0.30 * norm_sharpe) +
        (0.20 * norm_recency) +
        (0.10 * norm_cat) -
        copy_penalty
    )
    return round(max(0.0, min(100.0, composite)), 1)

def select_top_10_roster(
    candidates: List[Wallet], 
    current_incumbent_addresses: Optional[Set[str]] = None,
    hysteresis_buffer: float = 5.0
) -> List[Wallet]:
    """
    Roster Selection with 5-Point Hysteresis:
    Incumbent active whales receive a +5.0 point incumbency defense buffer during ranking.
    A challenger on the bench must beat the incumbent by >= 5.0 points to displace it.
    """
    incumbents = set(a.lower() for a in (current_incumbent_addresses or set()))

    def ranking_key(w: Wallet) -> float:
        base_score = float(w.baleen_score or 0.0)
        is_incumbent = w.address.lower() in incumbents
        defense_bonus = hysteresis_buffer if is_incumbent else 0.0
        gold_boost = 3.0 if w.tier == "gold_sniper" else 0.0
        return base_score + defense_bonus + gold_boost

    sorted_roster = sorted(candidates, key=ranking_key, reverse=True)
    return sorted_roster[:10]

async def get_active_basket(db: AsyncSession) -> list[Wallet]:
    """Returns the Top 10 active, non-dormant roster wallets."""
    stmt = select(Wallet).where(
        Wallet.status == "active",
        Wallet.dormant == False,
        Wallet.is_hft == False
    ).order_by(Wallet.baleen_score.desc()).limit(10)
    result = await db.execute(stmt)
    return result.scalars().all()

async def refresh_basket(db: AsyncSession):
    """
    24-Hour Rescore Cadence with Intra-Pool Normalization & 5-Point Hysteresis:
    Evaluates hard filters, computes normalized pool scores, and selects Top 10 roster.
    """
    stmt_active = select(Wallet.address).where(Wallet.status == "active")
    current_active_addrs = set((await db.execute(stmt_active)).scalars().all())

    stmt_all = select(Wallet).where(Wallet.status.in_(["active", "tracked"]))
    wallets = (await db.execute(stmt_all)).scalars().all()

    import json
    candidate_wallets = []
    candidate_stats_list = []

    for wallet in wallets:
        daily_hist = []
        if wallet.cached_daily_pnl:
            try:
                daily_hist = json.loads(wallet.cached_daily_pnl)
            except Exception:
                daily_hist = []

        stats = {
            'all_time_pnl_usd': wallet.all_time_pnl_usd,
            'avg_trades_per_day': wallet.avg_trades_per_day,
            'outlier_concentration_pct': wallet.outlier_concentration_pct,
            'win_rate_pct': wallet.win_rate_pct,
            'max_drawdown_pct': wallet.max_drawdown_pct,
            'trades_count': wallet.total_trades_analyzed,
            'daily_pnl_history': daily_hist,
            'is_hft': wallet.is_hft,
            'has_no_history': bool(not daily_hist and not wallet.all_time_pnl_usd)
        }
        
        score_res = score_wallet(stats)
        if score_res.status == "rejected":
            wallet.status = "rejected"
            wallet.tier = "rejected"
            wallet.rejection_reason = score_res.rejection_reason
        else:
            wallet.tier = score_res.tier
            candidate_wallets.append(wallet)
            candidate_stats_list.append(stats)
        wallet.last_scored_at = datetime.utcnow()

    # Dynamic Intra-Pool Normalization
    if candidate_stats_list:
        scores = normalize_and_score_pool(candidate_stats_list)
        for w, sc in zip(candidate_wallets, scores):
            w.baleen_score = sc

    # Select Top 10 Roster with 5-point Hysteresis
    qualifying_wallets = [w for w in candidate_wallets if not w.dormant]
    top_10 = select_top_10_roster(qualifying_wallets, current_incumbent_addresses=current_active_addrs, hysteresis_buffer=5.0)
    top_10_addrs = set(w.address.lower() for w in top_10)

    for w in qualifying_wallets:
        if w.address.lower() in top_10_addrs:
            w.status = "active"
        else:
            w.status = "tracked"

    await db.commit()
    logger.info(f"24h Pool-Normalized Roster Rescore Complete: {len(top_10)} active whales in Top 10 roster.")
