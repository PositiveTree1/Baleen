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
    Spec v2 Part C 5-Factor Formulation:
    1. S_winrate: Wilson 90% CI lower bound / odds-weighted edge (25% weight)
    2. S_consistency: Trailing 90-day period Sharpe ratio (25% weight)
    3. S_profitfactor: Gross wins / gross losses, target > 2.5 (20% weight)
    4. S_drawdown: 100 * (1 - drawdown% / 25%) (15% weight)
    5. S_recency: 30-day realized-PnL momentum EMA (15% weight)
    """
    win_rate = float(stats.get('win_rate_pct', 0) or 0)
    avg_price = stats.get('avg_entry_price')
    pnl = float(stats.get('all_time_pnl_usd', 0) or 0)
    daily_history = stats.get('daily_pnl_history') or []
    category_count = int(stats.get('category_count', 3) or 3)
    median_trade_size = float(stats.get('median_trade_size', 150.0) or 150.0)
    max_drawdown = float(stats.get('max_drawdown_pct', 10.0) or 10.0)

    # 1. S_winrate: Odds-weighted edge if avg_entry_price provided, else Wilson lower bound
    if avg_price is not None:
        implied_prob = max(0.05, min(0.95, float(avg_price)))
        actual_prob = win_rate / 100.0
        odds_edge = actual_prob - implied_prob
        norm_winrate = max(0.0, min(100.0, ((odds_edge + 0.10) / 0.35) * 100.0))
    else:
        wilson_lb = float(stats.get('wilson_lower_bound') or stats.get('wilson_lb') or 0.0)
        if 0.0 < wilson_lb <= 1.0:
            wilson_lb *= 100.0
        if wilson_lb <= 0.0:
            wilson_lb = win_rate
        norm_winrate = max(0.0, min(100.0, ((wilson_lb - 50.0) / 40.0) * 100.0))

    # 2. S_consistency: Trailing 90-day period Sharpe ratio on daily returns
    trailing_sharpe = float(stats.get('trailing_90d_sharpe') or stats.get('sharpe_ratio') or 0.0)
    if trailing_sharpe <= 0.0:
        if daily_history and len(daily_history) >= 3:
            nets = [float(h.get('net_pnl') or h.get('daily_pnl') or 0.0) for h in daily_history]
            mean_pnl = sum(nets) / len(nets)
            variance = sum((n - mean_pnl)**2 for n in nets) / len(nets)
            stdev = math.sqrt(variance)
            trailing_sharpe = mean_pnl / (stdev + 1e-6) if stdev > 0 else (1.5 if mean_pnl > 0 else 0.0)
        else:
            trailing_sharpe = 1.0

    # 3. S_profitfactor: Gross wins / gross losses, target > 2.5
    profit_factor = stats.get('profit_factor')
    if profit_factor is not None:
        pf_val = float(profit_factor)
    else:
        pf_val = 1.5 + min(1.5, pnl / 100000.0) if pnl > 0 else 1.0

    # 4. S_recency: 30-day realized-PnL momentum EMA
    recency_ema = float(stats.get('recency_ema', 0.0) or 0.0)
    if recency_ema == 0.0 and daily_history:
        alpha_30d = 1.0 - math.exp(-math.log(2) / 30.0)
        for h in daily_history:
            net_d = float(h.get("daily_pnl") or h.get("net_pnl") or 0.0)
            recency_ema = (1.0 - alpha_30d) * recency_ema + alpha_30d * net_d
    elif recency_ema == 0.0 and pnl > 0:
        recency_ema = pnl / 30.0

    # Category breadth bonus & copyability penalty
    cat_bonus = min(5.0, (float(category_count) / 3.0) * 5.0)
    copy_penalty = min(5.0, (median_trade_size / 5000.0) * 5.0)

    return {
        "norm_winrate": norm_winrate,
        "trailing_sharpe": trailing_sharpe,
        "profit_factor": pf_val,
        "max_drawdown": max_drawdown,
        "recency_ema": recency_ema,
        "cat_bonus": cat_bonus,
        "copy_penalty": copy_penalty
    }

def normalize_and_score_pool(candidate_stats_list: List[dict]) -> List[float]:
    """
    Spec v2 Part C: 5-Factor Composite Scoring across Candidate Pool:
    Score = (0.25 * S_winrate) + (0.25 * S_consistency) + (0.20 * S_profitfactor)
            + (0.15 * S_drawdown) + (0.15 * S_recency)
    """
    if not candidate_stats_list:
        return []

    raw_factors_list = [compute_raw_factors(s) for s in candidate_stats_list]
    final_scores = []

    for rf in raw_factors_list:
        # 1. S_winrate (25%)
        s_winrate = rf["norm_winrate"]

        # 2. S_consistency (25%): Trailing 90-day period Sharpe (target 2.5)
        s_consistency = max(0.0, min(100.0, (rf["trailing_sharpe"] / 2.5) * 100.0))

        # 3. S_profitfactor (20%): Target > 2.5
        s_profitfactor = max(0.0, min(100.0, (rf["profit_factor"] / 2.5) * 100.0))

        # 4. S_drawdown (15%): 100 * (1 - drawdown% / 25%)
        s_drawdown = max(0.0, min(100.0, 100.0 * (1.0 - rf["max_drawdown"] / 25.0)))

        # 5. S_recency (15%): Log-scaled EMA momentum
        s_recency = max(0.0, min(100.0, (math.log10(max(10.0, rf["recency_ema"])) / 4.0) * 100.0 if rf["recency_ema"] > 0 else 0.0))

        composite = (
            (0.25 * s_winrate) +
            (0.25 * s_consistency) +
            (0.20 * s_profitfactor) +
            (0.15 * s_drawdown) +
            (0.15 * s_recency) +
            rf["cat_bonus"] -
            rf["copy_penalty"]
        )
        scaled_score = round(max(0.0, min(100.0, composite)), 1)
        final_scores.append(scaled_score)

    return final_scores

def compute_baleen_score(stats: dict) -> float:
    """Computes standalone Baleen Score for a single wallet using Spec v2 Part C."""
    scores = normalize_and_score_pool([stats])
    return scores[0] if scores else 0.0

def compute_daily_pnl_correlation(daily_hist_a: List[dict], daily_hist_b: List[dict]) -> float:
    """
    Computes Pearson correlation coefficient r of daily realized PnL between two candidate wallets.
    Returns r between -1.0 and 1.0 (or 0.0 if insufficient overlap).
    """
    if not daily_hist_a or not daily_hist_b:
        return 0.0
    
    pnl_map_a = {str(h.get('date') or ''): float(h.get('daily_pnl') or h.get('net_pnl') or 0.0) for h in daily_hist_a if h.get('date')}
    pnl_map_b = {str(h.get('date') or ''): float(h.get('daily_pnl') or h.get('net_pnl') or 0.0) for h in daily_hist_b if h.get('date')}
    
    common_dates = sorted(set(pnl_map_a.keys()) & set(pnl_map_b.keys()))
    if len(common_dates) < 3:
        return 0.0
    
    vals_a = [pnl_map_a[d] for d in common_dates]
    vals_b = [pnl_map_b[d] for d in common_dates]
    
    mean_a = sum(vals_a) / len(vals_a)
    mean_b = sum(vals_b) / len(vals_b)
    
    dev_a = [x - mean_a for x in vals_a]
    dev_b = [y - mean_b for y in vals_b]
    
    sum_sq_a = sum(x * x for x in dev_a)
    sum_sq_b = sum(y * y for y in dev_b)
    
    if sum_sq_a <= 1e-9 or sum_sq_b <= 1e-9:
        return 0.0
    
    cov = sum(x * y for x, y in zip(dev_a, dev_b))
    r = cov / (math.sqrt(sum_sq_a * sum_sq_b) + 1e-9)
    return round(float(r), 4)

def select_top_10_roster(
    candidates: List[Wallet], 
    current_incumbent_addresses: Optional[Set[str]] = None,
    hysteresis_buffer: float = 5.0,
    target_size: int = 10,
    wallet_histories: Optional[Dict[str, List[dict]]] = None,
    wallet_categories: Optional[Dict[str, str]] = None
) -> List[Wallet]:
    """
    Spec v2 Roster Selection:
    1. 5-Point Hysteresis: Incumbent active whales receive a +5.0 point incumbency defense buffer.
    2. Gate 13 (Category Concentration Cap): Max 40% of the active roster from the same category.
    3. Gate 14 (Pairwise Correlation Filter): Candidate daily PnL correlation r <= 0.70 with all higher-ranked members.
    """
    if not candidates:
        return []

    incumbents = set(a.lower() for a in (current_incumbent_addresses or set()))

    def ranking_key(w: Wallet) -> float:
        base_score = float(getattr(w, 'baleen_score', 0.0) or 0.0)
        addr = str(getattr(w, 'address', '') or str(w)).lower()
        is_incumbent = addr in incumbents
        defense_bonus = hysteresis_buffer if is_incumbent else 0.0
        gold_boost = 3.0 if getattr(w, 'tier', '') == "gold_sniper" else 0.0
        return base_score + defense_bonus + gold_boost

    sorted_candidates = sorted(candidates, key=ranking_key, reverse=True)
    
    import json
    histories = dict(wallet_histories or {})
    categories = dict(wallet_categories or {})
    
    for w in sorted_candidates:
        addr = str(getattr(w, 'address', '') or str(w)).lower()
        if addr not in histories:
            cached = getattr(w, 'cached_daily_pnl', None)
            if cached:
                try:
                    histories[addr] = json.loads(cached) if isinstance(cached, str) else cached
                except Exception:
                    histories[addr] = []
            else:
                histories[addr] = []
        if addr not in categories:
            categories[addr] = getattr(w, 'ai_style_tag', None) or getattr(w, 'primary_category', None) or "General"

    max_per_category = max(1, int(target_size * 0.40)) if target_size > 1 else 1

    selected_roster: List[Wallet] = []
    category_counts: Dict[str, int] = {}

    for candidate in sorted_candidates:
        if len(selected_roster) >= target_size:
            break
            
        c_addr = str(getattr(candidate, 'address', '') or str(candidate)).lower()
        c_cat = categories.get(c_addr, "General")
        
        # Gate 13: Category Concentration Cap
        if target_size > 1 and category_counts.get(c_cat, 0) >= max_per_category and c_cat != "General":
            logger.info(f"Gate 13 Cap: Skipping candidate {c_addr} (category '{c_cat}' reached max {max_per_category})")
            continue
            
        # Gate 14: Pairwise Correlation Filter (r <= 0.70)
        c_hist = histories.get(c_addr, [])
        is_correlated = False
        for chosen in selected_roster:
            chosen_addr = str(getattr(chosen, 'address', '') or str(chosen)).lower()
            chosen_hist = histories.get(chosen_addr, [])
            r = compute_daily_pnl_correlation(chosen_hist, c_hist)
            if r > 0.70:
                is_correlated = True
                logger.info(f"Gate 14 Correlation: Skipping candidate {c_addr} (r={r:.2f} > 0.70 with {chosen_addr})")
                break
                
        if is_correlated:
            continue
            
        selected_roster.append(candidate)
        category_counts[c_cat] = category_counts.get(c_cat, 0) + 1

    # Backfill if target size was not reached due to strict diversity filters, without violating category cap
    if len(selected_roster) < target_size:
        for candidate in sorted_candidates:
            if candidate not in selected_roster:
                c_addr = str(getattr(candidate, 'address', '') or str(candidate)).lower()
                c_cat = categories.get(c_addr, "General")
                if target_size > 1 and category_counts.get(c_cat, 0) >= max_per_category and c_cat != "General":
                    continue
                selected_roster.append(candidate)
                category_counts[c_cat] = category_counts.get(c_cat, 0) + 1
                if len(selected_roster) >= target_size:
                    break

    return selected_roster

async def get_active_basket(db: AsyncSession) -> list[Wallet]:
    """Returns the Top 10 active, non-dormant roster wallets."""
    stmt = select(Wallet).where(
        Wallet.status == "active",
        Wallet.dormant == False,
        Wallet.is_hft == False
    ).order_by(Wallet.baleen_score.desc()).limit(10)
    result = await db.execute(stmt)
    return result.scalars().all()

async def refresh_basket(db: AsyncSession, trigger_type: str = "SCHEDULED_CRON"):
    """
    24-Hour Rescore Cadence with Intra-Pool Normalization, 5-Point Hysteresis,
    Gate 13 Category Concentration Cap, and Gate 14 Correlation Filter.
    """
    start_t = datetime.utcnow()
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

    # Build wallet_histories and wallet_categories mapping for Gates 13 & 14
    wallet_histories = {}
    wallet_categories = {}
    for w, st in zip(candidate_wallets, candidate_stats_list):
        addr = w.address.lower()
        wallet_histories[addr] = st.get('daily_pnl_history') or []
        wallet_categories[addr] = st.get('primary_category') or w.ai_style_tag or "General"

    # Select Top 10 Roster with 5-point Hysteresis, Gate 13 Cap, and Gate 14 Correlation filter
    qualifying_wallets = [w for w in candidate_wallets if not w.dormant]
    top_10 = select_top_10_roster(
        qualifying_wallets, 
        current_incumbent_addresses=current_active_addrs, 
        hysteresis_buffer=5.0,
        target_size=10,
        wallet_histories=wallet_histories,
        wallet_categories=wallet_categories
    )
    top_10_addrs = set(w.address.lower() for w in top_10)

    for w in qualifying_wallets:
        if w.address.lower() in top_10_addrs:
            w.status = "active"
        else:
            w.status = "tracked"

    # Audit logging for re-evaluation in Supabase
    try:
        from app.models import SandboxRun, SandboxReevaluation
        stmt_run = select(SandboxRun).where(SandboxRun.status == "ACTIVE").order_by(SandboxRun.started_at.desc()).limit(1)
        active_run = (await db.execute(stmt_run)).scalars().first()

        promotions = [
            {"address": w.address, "name": w.name or w.pseudonym, "score": w.baleen_score}
            for w in top_10 if w.address.lower() not in set(a.lower() for a in current_active_addrs)
        ]
        demotions = [
            {"address": a, "reason": "Displaced by higher scoring candidate"}
            for a in current_active_addrs if a.lower() not in top_10_addrs
        ]
        top10_roster_json = [
            {
                "rank": idx + 1,
                "address": w.address,
                "name": w.name or w.pseudonym or "Whale",
                "tier": w.tier,
                "score": w.baleen_score,
                "win_rate": w.win_rate_pct,
                "pnl": w.all_time_pnl_usd,
                "trades_per_day": w.avg_trades_per_day
            }
            for idx, w in enumerate(top_10)
        ]

        duration_ms = (datetime.utcnow() - start_t).total_seconds() * 1000.0

        reeval_log = SandboxReevaluation(
            run_id=active_run.id if active_run else None,
            timestamp=datetime.utcnow(),
            trigger_type=trigger_type,
            total_candidates_scanned=len(wallets),
            qualified_whales_count=len(qualifying_wallets),
            top10_active_roster=top10_roster_json,
            promotions=promotions,
            demotions=demotions,
            execution_duration_ms=round(duration_ms, 1)
        )
        db.add(reeval_log)

        if active_run:
            active_run.total_reevaluations_count = (active_run.total_reevaluations_count or 0) + 1
            active_run.active_whales_roster = top10_roster_json
    except Exception as audit_err:
        logger.warning(f"Note on re-evaluation audit log: {audit_err}")

    await db.commit()
    logger.info(f"24h Pool-Normalized Roster Rescore Complete ({trigger_type}): {len(top_10)} active whales in Top 10 roster.")
