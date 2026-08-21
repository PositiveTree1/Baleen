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
    Scores a wallet based on exact §4 rules.
    """
    pnl = wallet_stats.get('all_time_pnl_usd', 0)
    trades_per_day = wallet_stats.get('avg_trades_per_day', 0)
    outlier_pct = wallet_stats.get('outlier_concentration_pct', 0)
    win_rate = wallet_stats.get('win_rate_pct', 0)
    max_drawdown = wallet_stats.get('max_drawdown_pct', 0)

    # FILTER 1: Minimum realized PnL >= $50,000
    if pnl < 50000:
        return ScoringResult("rejected", None, "PNL_BELOW_THRESHOLD", False)

    # FILTER 2: Anti-HFT (only reject high-frequency automated market maker bots >300 trades/day)
    if trades_per_day > 300:
        return ScoringResult("rejected", None, "HFT_EXCEEDED", False)

    # FILTER 3: Outlier concentration (max_single_trade_profit/realized_pnl <= 0.35)
    if outlier_pct > 0.35:
        return ScoringResult("rejected", None, "OUTLIER_CONCENTRATION_TOO_HIGH", False)

    # FILTER 4: Minimum Win Rate >= 55.0% (reject losing wallets with negative alpha)
    if win_rate < 55.0:
        return ScoringResult("rejected", None, "WIN_RATE_TOO_LOW", False)

    # TIER: Gold Sniper if win_rate >= 80.0% OR (pnl >= $100,000 and win_rate >= 70.0%)
    if (win_rate >= 80.0 and max_drawdown <= 15.0) or (pnl >= 100000 and win_rate >= 70.0):
        tier = "gold_sniper"
    else:
        tier = "standard"

    # Copyability check (flag, don't reject)
    copyability_flag = False
    
    return ScoringResult("active", tier, None, copyability_flag)
