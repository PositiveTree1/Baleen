from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SleeveAllocation:
    wallet_address: str
    base_budget_usd: float
    adjusted_budget_usd: float
    deployed_notional_usd: float
    free_sleeve_cash_usd: float
    copy_pnl_ema_usd: float = 0.0
    capture_rate_pct: float = 100.0
    trailing_trade_sizes: List[float] = field(default_factory=list)

@dataclass
class SleeveSizingResult:
    intended_size_usd: float
    actual_size_usd: float
    conviction_percentile: float
    capture_rate_pct: float
    is_clipped: bool
    status: str
    sleeve_remaining_usd: float

class SleeveManager:
    """
    10-Wallet Sleeve Architecture:
    1. Dynamic even split: bankroll / active_roster_size (~$1,000 each on $10k/10).
    2. Conviction Percentile sizing within sleeve: size = sleeve_remaining * conviction_percentile.
    3. Per-sleeve capital cap (no global starvation).
    4. Copy-PnL EMA dynamic sleeve adjustment with 0.30x floor and 1.50x cap.
    5. First-class capture rate metric logging.
    """

    @staticmethod
    def calculate_sleeve_budget(total_bankroll: float, active_roster_size: int = 10) -> float:
        """Dynamic even split of bankroll across active roster."""
        if active_roster_size <= 0:
            return 0.0
        return round(max(0.0, total_bankroll) / float(active_roster_size), 2)

    @staticmethod
    def calculate_conviction_percentile(trade_size_usd: float, trailing_sizes: List[float]) -> float:
        """
        Computes where this trade size ranks against the whale's own trailing trade sizes (0.05 to 1.0).
        Preserves the signal 'this trade is unusually big for this whale' without net-worth guessing.
        """
        if not trailing_sizes:
            return 0.50
        
        valid_sizes = [s for s in trailing_sizes if s > 0]
        if not valid_sizes:
            return 0.50

        # Percentile rank: fraction of past trades smaller or equal to current trade
        smaller_or_equal = sum(1 for s in valid_sizes if s <= trade_size_usd)
        percentile = float(smaller_or_equal) / float(len(valid_sizes))
        
        # Clamp between 0.05 (feeler) and 1.0 (max conviction)
        return round(max(0.05, min(1.0, percentile)), 4)

    @staticmethod
    def update_copy_pnl_ema(current_ema: float, new_realized_pnl: float, alpha: float = 0.05) -> float:
        """
        Slow Exponential Moving Average of Baleen's actual copy-PnL on this wallet.
        alpha = 0.05 ensures a long window (20+ trades) so we don't cut skilled wallets on short drawdown.
        """
        return round((1.0 - alpha) * current_ema + alpha * new_realized_pnl, 4)

    @staticmethod
    def calculate_adjusted_sleeve_budget(base_budget: float, copy_pnl_ema: float = 0.0, baleen_score: float = 80.0) -> float:
        """
        Adjusts sleeve budget dynamically off Baleen Score base weight + copy-PnL EMA
        with a strict 0.30x ($300) floor and 1.50x ($1,500) cap.
        """
        if base_budget <= 0:
            return 0.0
        
        # Base multiplier from Baleen Score normalized against benchmark 80.0
        score_factor = (baleen_score / 80.0) if baleen_score > 0 else 1.0
        # Scaling: each $100 in average realized copy-PnL adjusts budget by ~20%
        pnl_factor = (copy_pnl_ema / 500.0)
        multiplier = score_factor + pnl_factor
        clamped_multiplier = max(0.30, min(1.50, multiplier))
        return round(base_budget * clamped_multiplier, 2)

    @classmethod
    def size_sleeve_trade(
        cls,
        wallet_address: str,
        whale_trade_size_usd: float,
        sleeve_budget_usd: float,
        open_notional_usd: float,
        trailing_sizes: List[float],
        min_trade_usd: float = 5.0,
        quality_multiplier: float = 1.0
    ) -> SleeveSizingResult:
        """
        Sizes a trade strictly within its isolated wallet sleeve.
        """
        sleeve_remaining = max(0.0, sleeve_budget_usd - open_notional_usd)

        if sleeve_remaining < min_trade_usd:
            return SleeveSizingResult(
                intended_size_usd=0.0,
                actual_size_usd=0.0,
                conviction_percentile=0.0,
                capture_rate_pct=0.0,
                is_clipped=True,
                status="SKIPPED_SLEEVE_EXHAUSTED",
                sleeve_remaining_usd=round(sleeve_remaining, 2)
            )

        # 1. Calculate Conviction Percentile from trailing trade sizes
        conviction_pct = cls.calculate_conviction_percentile(whale_trade_size_usd, trailing_sizes)

        # 2. Intended size = sleeve_budget * conviction_percentile * quality_multiplier
        intended_size = round(sleeve_budget_usd * conviction_pct * quality_multiplier, 2)
        intended_size = max(min_trade_usd, intended_size)

        # 3. Clip strictly to available sleeve remaining
        actual_size = round(min(intended_size, sleeve_remaining), 2)

        if actual_size < min_trade_usd:
            return SleeveSizingResult(
                intended_size_usd=intended_size,
                actual_size_usd=0.0,
                conviction_percentile=conviction_pct,
                capture_rate_pct=0.0,
                is_clipped=True,
                status="SKIPPED_BELOW_MINIMUM",
                sleeve_remaining_usd=round(sleeve_remaining, 2)
            )

        is_clipped = (actual_size < intended_size - 0.01)
        capture_rate = round((actual_size / intended_size * 100.0) if intended_size > 0 else 100.0, 1)

        return SleeveSizingResult(
            intended_size_usd=intended_size,
            actual_size_usd=actual_size,
            conviction_percentile=conviction_pct,
            capture_rate_pct=capture_rate,
            is_clipped=is_clipped,
            status="SUCCESS",
            sleeve_remaining_usd=round(sleeve_remaining, 2)
        )
