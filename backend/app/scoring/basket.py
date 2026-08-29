import math
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Wallet
from app.scoring.engine import score_wallet

logger = logging.getLogger(__name__)

def compute_baleen_score(stats: dict) -> float:
    """
    5-Factor Quantitative Composite Whale Scoring (0 - 100):
    1. Risk-Adjusted Return (Sortino / Sharpe on Trade PnL series) — 25 pts
    2. Odds-Weighted Calibration / Brier Edge — 25 pts
    3. Category Breadth / Multi-Market Edge — 20 pts
    4. Recency-Weighted Momentum / EMA — 15 pts
    5. Copyability & Liquidity Score — 15 pts
    """
    pnl = float(stats.get('all_time_pnl_usd', 0) or 0)
    win_rate = float(stats.get('win_rate_pct', 0) or 0)
    drawdown = float(stats.get('max_drawdown_pct', 10) or 10)
    daily_history = stats.get('daily_pnl_history') or []
    trades_count = int(stats.get('trades_count', 0) or stats.get('total_trades_analyzed', 0) or 0)
    category_count = int(stats.get('category_count', 3) or 3)
    avg_price = float(stats.get('avg_entry_price', 0.50) or 0.50)

    # ---------------------------------------------------------
    # FACTOR 1: Risk-Adjusted Return (Sortino Ratio) — 25 points
    # ---------------------------------------------------------
    sortino_score = 15.0  # default baseline
    if daily_history and len(daily_history) >= 5:
        nets = [float(h.get('net_pnl') or h.get('daily_pnl') or 0.0) for h in daily_history]
        mean_pnl = sum(nets) / len(nets)
        downside_sq = [min(0.0, n)**2 for n in nets]
        downside_dev = math.sqrt(sum(downside_sq) / len(downside_sq)) if downside_sq else 1.0

        if downside_dev > 0:
            sortino_ratio = max(0.0, mean_pnl / downside_dev)
            # Sortino > 2.0 is institutional grade
            sortino_score = min(25.0, sortino_ratio * 10.0)
        else:
            sortino_score = 25.0 if mean_pnl > 0 else 5.0
    else:
        # Fallback to drawdown-penalized PnL score
        dd_shield = max(0.0, 1.0 - (drawdown / 30.0))
        pnl_component = min(1.0, max(0.0, pnl) / 500000.0)
        sortino_score = (dd_shield * 15.0) + (pnl_component * 10.0)

    # ---------------------------------------------------------
    # FACTOR 2: Odds-Weighted Calibration / Brier Edge — 25 points
    # ---------------------------------------------------------
    # A 65% win rate buying 40% underdogs is vastly superior to 65% buying 85% favorites!
    implied_prob = max(0.10, min(0.90, avg_price))
    actual_prob = win_rate / 100.0
    calibration_edge = actual_prob - implied_prob

    if calibration_edge > 0:
        # +15% edge over market odds gets full 25 points
        odds_score = min(25.0, 10.0 + (calibration_edge / 0.15) * 15.0)
    else:
        # Penalize negative edge over market odds
        odds_score = max(5.0, 10.0 + (calibration_edge / 0.15) * 10.0)

    # ---------------------------------------------------------
    # FACTOR 3: Category Breadth & Non-Concentration — 20 points
    # ---------------------------------------------------------
    # Whales whose edge spans Politics, Sports, Tech, Macro get full points
    if category_count >= 4:
        breadth_score = 20.0
    elif category_count == 3:
        breadth_score = 16.0
    elif category_count == 2:
        breadth_score = 12.0
    else:
        breadth_score = 8.0

    # ---------------------------------------------------------
    # FACTOR 4: Recency-Weighted Performance (30-Day EMA) — 15 points
    # ---------------------------------------------------------
    if daily_history and len(daily_history) >= 10:
        # Last 30 daily data points vs all-time
        recent_30 = daily_history[-30:] if len(daily_history) >= 30 else daily_history
        recent_pos = sum(1 for h in recent_30 if float(h.get('net_pnl') or h.get('daily_pnl') or 0) > 0)
        recent_win_rate = (recent_pos / len(recent_30)) if recent_30 else 0.5
        recency_score = min(15.0, max(3.0, (recent_win_rate / 0.75) * 15.0))
    else:
        # Volume-weighted track record bonus
        track_bonus = min(1.0, trades_count / 150.0)
        recency_score = 5.0 + (track_bonus * 10.0)

    # ---------------------------------------------------------
    # FACTOR 5: Copyability & Liquidity Score — 15 points
    # ---------------------------------------------------------
    # Rewards thick liquid order books and reasonable trade counts
    is_hft = stats.get('is_hft', False)
    avg_trades_day = float(stats.get('avg_trades_per_day', 5) or 5)
    
    if is_hft or avg_trades_day > 80:
        copyability_score = 4.0
    elif avg_trades_day > 30:
        copyability_score = 9.0
    else:
        copyability_score = 15.0

    total_score = sortino_score + odds_score + breadth_score + recency_score + copyability_score
    return round(min(100.0, max(0.0, total_score)), 1)

def select_top_10_roster(
    candidates: List[Wallet], 
    current_incumbent_addresses: Optional[Set[str]] = None,
    hysteresis_buffer: float = 5.0
) -> List[Wallet]:
    """
    Roster Selection with 5-Point Hysteresis:
    Incumbent active whales receive a +5.0 point incumbency defense buffer during ranking.
    A challenger on the bench must beat the incumbent by >= 5.0 points to displace it,
    completely eliminating frivolous roster churn.
    """
    incumbents = set(a.lower() for a in (current_incumbent_addresses or set()))

    def ranking_key(w: Wallet) -> float:
        base_score = float(w.baleen_score or 0.0)
        is_incumbent = w.address.lower() in incumbents
        # Incumbent defense bonus
        defense_bonus = hysteresis_buffer if is_incumbent else 0.0
        # Tier bonus: Gold Snipers get secondary boost
        gold_boost = 3.0 if w.tier == "gold_sniper" else 0.0
        return base_score + defense_bonus + gold_boost

    # Sort descending by effective score
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
    24-Hour Rescore Cadence with 5-Point Hysteresis:
    Rescores all qualifying wallets and updates active Top 10 roster.
    """
    # 1. Fetch current active incumbent addresses
    stmt_active = select(Wallet.address).where(Wallet.status == "active")
    current_active_addrs = set((await db.execute(stmt_active)).scalars().all())

    # 2. Fetch all tracked and active wallets
    stmt_all = select(Wallet).where(Wallet.status.in_(["active", "tracked"]))
    wallets = (await db.execute(stmt_all)).scalars().all()

    import json
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
            wallet.baleen_score = compute_baleen_score(stats)
        wallet.last_scored_at = datetime.utcnow()

    # 3. Select Top 10 Roster with Hysteresis
    qualifying_wallets = [w for w in wallets if w.status != "rejected" and not w.dormant]
    top_10 = select_top_10_roster(qualifying_wallets, current_incumbent_addresses=current_active_addrs, hysteresis_buffer=5.0)
    top_10_addrs = set(w.address.lower() for w in top_10)

    for w in qualifying_wallets:
        if w.address.lower() in top_10_addrs:
            w.status = "active"
        else:
            w.status = "tracked"

    await db.commit()
    logger.info(f"24h Roster Rescore Complete: {len(top_10)} active whales in Top 10 roster.")
