from dataclasses import dataclass
from typing import Optional

@dataclass
class ScoringResult:
    status: str
    tier: Optional[str]
    rejection_reason: Optional[str]
    copyability_flag: bool

def score_wallet(wallet_stats: dict) -> ScoringResult:
    """
    Titan / Claude Top-10 Quantitative Screening Engine:
    Applies strict hard disqualifying filters before scoring.
    """
    pnl = float(wallet_stats.get('all_time_pnl_usd', 0) or 0)
    trades_per_day = float(wallet_stats.get('avg_trades_per_day', 0) or 0)
    outlier_pct = float(wallet_stats.get('outlier_concentration_pct', 0) or 0)
    win_rate = float(wallet_stats.get('win_rate_pct', 0) or 0)
    max_drawdown = float(wallet_stats.get('max_drawdown_pct', 0) or 0)
    trades_count = int(wallet_stats.get('trades_count', 0) or 0)

    # FILTER 1: Minimum realized PnL >= $50,000
    if pnl < 50000.0:
        return ScoringResult("rejected", None, "PNL_BELOW_THRESHOLD", False)

    # FILTER 2: Track record length (minimum 100 resolved trades if evaluated in full)
    if trades_count > 0 and trades_count < 100 and pnl < 250000.0:
        return ScoringResult("rejected", None, "INSUFFICIENT_TRACK_RECORD_LENGTH", False)

    # FILTER 3: Market concentration (no single trade > 25% of lifetime realized PnL)
    if outlier_pct > 0.25:
        return ScoringResult("rejected", None, "OUTLIER_CONCENTRATION_TOO_HIGH", False)

    # FILTER 4: Anti-HFT (reject automated market maker bots >100 trades/day)
    if trades_per_day > 100.0:
        return ScoringResult("rejected", None, "HFT_EXCEEDED", False)

    # FILTER 5: Minimum Win Rate >= 55.0%
    if win_rate < 55.0:
        return ScoringResult("rejected", None, "WIN_RATE_TOO_LOW", False)

    # FILTER 6: Boundary Arbitrage Bot Filter (reject toxic 0.01/0.99 snipers)
    if wallet_stats.get('is_boundary_arb'):
        return ScoringResult("rejected", None, "ARBITRAGE_BOUNDARY_SNIPER", False)

    # FILTER 7: Wash / Circular Trading Filter
    if wallet_stats.get('is_wash_trading'):
        return ScoringResult("rejected", None, "WASH_TRADING_PATTERN", False)

    # FILTER 8: Mandatory On-Chain History Requirement
    if wallet_stats.get('has_no_history'):
        return ScoringResult("rejected", None, "MISSING_ONCHAIN_HISTORY", False)

    # TIER: Gold Sniper requires win_rate >= 80.0% AND max_drawdown <= 12.0%
    if win_rate >= 80.0 and max_drawdown <= 12.0:
        tier = "gold_sniper"
    else:
        tier = "standard"

    return ScoringResult("active", tier, None, True)
