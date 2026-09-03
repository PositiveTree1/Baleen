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
    Claude / Titan Disqualifying Hard Filters:
    Computed once per wallet, re-checked every 24h rescore.
    Only wallets passing 100% of these hard filters advance to 5-factor ranking.
    """
    pnl = float(wallet_stats.get('all_time_pnl_usd', 0) or 0)
    vol = float(wallet_stats.get('total_volume_usd', 0) or 0)
    trades_per_day = float(wallet_stats.get('avg_trades_per_day', 0) or 0)
    outlier_pct = float(wallet_stats.get('outlier_concentration_pct', 0) or 0)
    win_rate = float(wallet_stats.get('win_rate_pct', 0) or 0)
    max_drawdown = float(wallet_stats.get('max_drawdown_pct', 0) or 0)
    trades_count = int(wallet_stats.get('trades_count', 0) or wallet_stats.get('total_trades_analyzed', 0) or 0)
    active_days = float(wallet_stats.get('active_days', 60.0) or 60.0)

    # FILTER 0: Conflicting Positions / Hedging Disqualification (Kick them out immediately)
    if wallet_stats.get('is_conflicting_positions'):
        return ScoringResult("rejected", None, "CONFLICTING_POSITIONS_DETECTED", False)

    # FILTER 1: Minimum Realized PnL >= $50,000 and Minimum Volume >= $150,000
    if pnl < 50000.0:
        return ScoringResult("rejected", None, "PNL_BELOW_THRESHOLD", False)
    
    if vol > 0 and vol < 150000.0 and pnl < 250000.0:
        return ScoringResult("rejected", None, "VOLUME_BELOW_THRESHOLD", False)

    # FILTER 2: Track record length (>= 150 lifetime trades AND >= 60 active days)
    if trades_count < 150 and pnl < 500000.0:
        return ScoringResult("rejected", None, "INSUFFICIENT_TRACK_RECORD_TRADES", False)
    
    if active_days < 60.0 and pnl < 500000.0:
        return ScoringResult("rejected", None, "INSUFFICIENT_ACTIVE_HISTORY_DAYS", False)

    # FILTER 3: Not an HFT/market-making bot (trades_per_day <= 65.0)
    if trades_per_day > 65.0:
        return ScoringResult("rejected", None, "HFT_MAKER_BOT_EXCEEDED", False)

    # FILTER 4: Position concentration cap (no single position > 25% of positive realized PnL sum)
    if outlier_pct > 0.25:
        return ScoringResult("rejected", None, "OUTLIER_CONCENTRATION_TOO_HIGH", False)

    # FILTER 5: Sleeve size compatibility ($20 <= median trade size <= $3,000)
    if wallet_stats.get('is_sleeve_incompatible'):
        return ScoringResult("rejected", None, "SLEEVE_SIZE_INCOMPATIBLE", False)

    # FILTER 6: Wash-trading / round-trip detection (<120s BUY<->SELL pairs > 10%)
    if wallet_stats.get('is_wash_trading'):
        return ScoringResult("rejected", None, "WASH_TRADING_PATTERN", False)

    # FILTER 7: Mandatory on-chain history requirement
    if wallet_stats.get('has_no_history'):
        return ScoringResult("rejected", None, "MISSING_ONCHAIN_HISTORY", False)

    # FILTER 8: Boundary Arbitrage Bot Filter (reject toxic 0.01/0.99 snipers)
    if wallet_stats.get('is_boundary_arb'):
        return ScoringResult("rejected", None, "ARBITRAGE_BOUNDARY_SNIPER", False)

    # FILTER 9: Minimum Win Rate >= 55.0%
    if win_rate < 55.0:
        return ScoringResult("rejected", None, "WIN_RATE_TOO_LOW", False)

    # FILTER 10: Reconstructed Cumulative PnL Verification (Must be strictly positive)
    cum_pnl = float(wallet_stats.get('cumulative_pnl', pnl) if wallet_stats.get('cumulative_pnl') is not None else pnl)
    if cum_pnl <= 0.0:
        return ScoringResult("rejected", None, "RECONSTRUCTED_PNL_NON_POSITIVE", False)

    # FILTER 11: Open Position Paper Loss Bleed Gate (Reject active bleed > $25k or > 35% of total PnL)
    unrealized_open_pnl = float(wallet_stats.get('unrealized_open_pnl', 0.0) or 0.0)
    if unrealized_open_pnl < -25000.0 or (pnl > 0 and abs(min(0.0, unrealized_open_pnl)) > 0.35 * pnl):
        return ScoringResult("rejected", None, "OPEN_POSITION_DRAWDOWN_EXCEEDED", False)

    # FILTER 12: Maximum Drawdown Hard Cap (Must not exceed 25.0%)
    if max_drawdown > 25.0:
        return ScoringResult("rejected", None, "DRAWDOWN_TOO_HIGH", False)

    # FILTER 13: Inconsistent / Deceptive Lumpy Profile Disqualification
    if wallet_stats.get('is_inconsistent_profile'):
        return ScoringResult("rejected", None, "INCONSISTENT_LUMPY_PROFILE", False)

    # TIER: Gold Sniper requires win_rate >= 80.0%, max_drawdown <= 12.0%, and healthy open positions
    if win_rate >= 80.0 and max_drawdown <= 12.0 and unrealized_open_pnl >= -5000.0:
        tier = "gold_sniper"
    else:
        tier = "standard"

    return ScoringResult("active", tier, None, True)
