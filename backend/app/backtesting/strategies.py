"""
Copy-Trading Strategy Definitions for Backtesting
Implements baseline, conviction sleeve, fee-gated, anti-conflict, and full adaptive strategies.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set
from app.backtesting.models import TradeSignal, ClosedTrade
from app.backtesting.portfolio import SimulatedPortfolio
from app.sizing.sleeve_manager import SleeveManager
from app.services.polymarket_fees import calculate_polymarket_fee, classify_market_category

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        """Returns intended order size in USD, or None/0.0 to skip signal."""
        pass

    def on_trade_closed(self, trade: ClosedTrade):
        """Optional hook called when an order exits or settles."""
        pass


class FixedProportionalStrategy(BaseStrategy):
    """Simple baseline strategy: allocates a fixed percentage of total portfolio per trade."""
    def __init__(self, fraction: float = 0.03, name: str = "FixedProportional_3pct"):
        super().__init__(name)
        self.fraction = fraction

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None  # Only initiate on BUY, sells handled automatically by portfolio
        intended = portfolio.initial_capital * self.fraction
        return round(intended, 2)


class SleeveConvictionStrategy(BaseStrategy):
    """
    Baleen Conviction Percentile Sizing:
    Sizes each order by ranking the whale's trade size against their own trailing trade history.
    """
    def __init__(self, name: str = "SleeveConviction"):
        super().__init__(name)
        self.trailing_sizes: Dict[str, List[float]] = {}

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        clean_whale = signal.whale_address.lower()
        sizes = self.trailing_sizes.setdefault(clean_whale, [])
        sizes.append(signal.whale_size_usd)
        if len(sizes) > 100:
            sizes.pop(0)

        if signal.side.upper() != "BUY":
            return None

        # Calculate conviction percentile (0.05 to 1.0)
        conviction = SleeveManager.calculate_conviction_percentile(signal.whale_size_usd, sizes)
        sleeve_cash = portfolio.get_available_sleeve_cash(clean_whale)
        budget = portfolio.sleeve_budgets.get(clean_whale, portfolio.config.initial_capital * portfolio.config.max_sleeve_fraction)
        
        intended = budget * conviction
        return round(min(intended, sleeve_cash), 2)


class FeeAwareGatedStrategy(SleeveConvictionStrategy):
    """
    EV-Gated Sleeve Strategy:
    Rejects copy signals where Expected Edge does not clear the fee hurdle:
    Expected Edge > ev_multiplier * [Theta * (1 - p)].
    """
    def __init__(self, ev_multiplier: float = 2.5, name: str = "FeeAware_EV_Gate"):
        super().__init__(name=name)
        self.ev_multiplier = ev_multiplier

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        base_size = super().evaluate_signal(signal, portfolio)
        if not base_size or base_size <= 0:
            return None

        p = max(0.01, min(0.99, signal.whale_price))
        _, theta = classify_market_category(signal.market_title or signal.category)
        fee_rate = theta * (1.0 - p)
        min_required_edge = self.ev_multiplier * fee_rate

        # Estimated statistical edge for high-winrate whale
        # In prediction markets, trading near 0.50 with fee rate 3% requires substantial edge
        assumed_whale_edge = max(0.01, (0.70 - p)) if p < 0.70 else 0.03
        if assumed_whale_edge < min_required_edge:
            return None  # Blocked by fee-aware EV gate

        return base_size


class AntiConflictGatedStrategy(SleeveConvictionStrategy):
    """
    Anti-Conflict Gate Strategy:
    Disqualifies any whale that trades opposing mutually exclusive positions (YES and NO on the same market).
    """
    def __init__(self, max_conflict_tolerance: float = 0.15, name: str = "AntiConflict_Gated"):
        super().__init__(name=name)
        self.max_conflict_tolerance = max_conflict_tolerance
        self.whale_market_sides: Dict[str, Dict[str, Set[str]]] = {} # whale -> {condition_id -> {token1, token2}}
        self.disqualified_whales: Set[str] = set()

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        clean_whale = signal.whale_address.lower()
        if clean_whale in self.disqualified_whales:
            return None

        # Track sides only on BUY entries
        if signal.side.upper() == "BUY":
            m_dict = self.whale_market_sides.setdefault(clean_whale, {})
            m_key = signal.condition_id or signal.market_id
            sides = m_dict.setdefault(m_key, set())
            sides.add(signal.nonusdc_side)

            # Check conflict ratio
            conflicts = sum(1 for s in m_dict.values() if len(s) > 1)
            total_mkts = max(1, len(m_dict))
            if conflicts >= 1 and (conflicts / total_mkts) > self.max_conflict_tolerance:
                self.disqualified_whales.add(clean_whale)
                return None

        return super().evaluate_signal(signal, portfolio)


class AdaptiveProductionStrategy(BaseStrategy):
    """
    The Premier Baleen Strategy:
    1. Disqualifies conflicting and hedged wallets.
    2. Uses Sleeve Conviction Percentile sizing.
    3. Fee-aware EV gate (2.5x taker fee hurdle).
    4. Copy-PnL EMA dynamic sleeve capital adjustment with 0.30x floor and 1.50x cap.
    5. Dynamic risk throttling under sleeve drawdown.
    """
    def __init__(self, ev_multiplier: float = 2.5, max_conflict_ratio: float = 0.15, name: str = "BaleenAdaptiveProduction"):
        super().__init__(name=name)
        self.ev_multiplier = ev_multiplier
        self.max_conflict_ratio = max_conflict_ratio
        self.trailing_sizes: Dict[str, List[float]] = {}
        self.whale_market_sides: Dict[str, Dict[str, Set[str]]] = {}
        self.disqualified_whales: Set[str] = set()
        self.copy_pnl_ema: Dict[str, float] = {}

    def on_trade_closed(self, trade: ClosedTrade):
        w = trade.whale_address.lower()
        curr_ema = self.copy_pnl_ema.get(w, 0.0)
        self.copy_pnl_ema[w] = SleeveManager.update_copy_pnl_ema(curr_ema, trade.net_pnl)

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        clean_whale = signal.whale_address.lower()

        # 1. Anti-Conflict Position Gate
        if clean_whale in self.disqualified_whales:
            return None

        if signal.side.upper() != "BUY":
            return None

        m_dict = self.whale_market_sides.setdefault(clean_whale, {})
        m_key = signal.condition_id or signal.market_id
        sides = m_dict.setdefault(m_key, set())
        sides.add(signal.nonusdc_side)

        conflicts = sum(1 for s in m_dict.values() if len(s) > 1)
        total_mkts = max(1, len(m_dict))
        if conflicts >= 1 and (conflicts / total_mkts) > self.max_conflict_ratio:
            self.disqualified_whales.add(clean_whale)
            return None

        # 2. Fee-Aware EV Gate
        p = max(0.01, min(0.99, signal.whale_price))
        _, theta = classify_market_category(signal.market_title or signal.category)
        fee_rate = theta * (1.0 - p)
        min_required_edge = self.ev_multiplier * fee_rate

        # Estimated statistical edge
        assumed_whale_edge = max(0.01, (0.72 - p)) if p < 0.72 else 0.035
        if assumed_whale_edge < min_required_edge:
            return None

        # 3. Conviction Percentile Sizing
        sizes = self.trailing_sizes.setdefault(clean_whale, [])
        sizes.append(signal.whale_size_usd)
        if len(sizes) > 100:
            sizes.pop(0)

        conviction = SleeveManager.calculate_conviction_percentile(signal.whale_size_usd, sizes)

        # 4. Dynamic Sleeve Budget with Copy-PnL EMA
        base_budget = portfolio.sleeve_budgets.get(clean_whale, portfolio.config.initial_capital * portfolio.config.max_sleeve_fraction)
        ema = self.copy_pnl_ema.get(clean_whale, 0.0)
        adjusted_budget = SleeveManager.calculate_adjusted_sleeve_budget(base_budget, copy_pnl_ema=ema)

        sleeve_cash = portfolio.get_available_sleeve_cash(clean_whale)
        intended = adjusted_budget * conviction
        final_size = min(intended, sleeve_cash)

        if final_size < portfolio.config.min_trade_size_usd:
            return None

        return round(final_size, 2)
