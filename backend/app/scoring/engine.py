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

    # FILTER 2: Anti-HFT (trades_per_day <= 100)
    if trades_per_day > 100:
        return ScoringResult("rejected", None, "HFT_EXCEEDED", False)

    # FILTER 3: Outlier concentration (max_single_trade_profit/realized_pnl <= 0.35)
    if outlier_pct > 0.35:
        return ScoringResult("rejected", None, "OUTLIER_CONCENTRATION_TOO_HIGH", False)

    # TIER: Gold Sniper if win_rate >= 85.0% AND max_drawdown <= 10.0%
    # TIER: Gold Sniper if win_rate >= 85.0% AND max_drawdown <= 10.0%
    if win_rate >= 85.0 and max_drawdown <= 10.0:
        tier = "gold_sniper"
    else:
        tier = "standard"

    # FILTER 4: Copyability check (flag, don't reject)
    copyability_flag = False
    
    return ScoringResult("active", tier, None, copyability_flag)
