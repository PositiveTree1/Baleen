"""
Quantitative Copy-Trading Strategy Suite for Backtesting
Implements:
  1. Fixed Amount Entry ($100 Fixed Entry)
  2. Fixed Proportional (1%, 2%, 3% Bankroll Sizing)
  3. High-Conviction Gold Snipers Only (Win Rate >= 80%, Conviction >= 70th Percentile)
  4. Consensus / Multi-Whale Confirmation (2+ Whales Buy the Same Outcome within 24h)
  5. Top Whales by Sharpe (Dynamic Half-Kelly Sizing)
  6. Resolution Hold ("Diamond Hands" - Hold Contract to Official Resolution Payout)
  7. Whale Exit Mirroring (Mirror Whale Early Exits)
  8. Anti-Conflict Gated (Disqualify Hedged / Counter-Trading Wallets)
  9. Adaptive Production Strategy (Flagship Baleen Production Engine)
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple
from app.backtesting.models import TradeSignal, ClosedTrade, WhaleQualification
from app.backtesting.portfolio import SimulatedPortfolio
from app.sizing.sleeve_manager import SleeveManager
from app.services.polymarket_fees import classify_market_category

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

    def should_mirror_whale_exit(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> bool:
        """Determines whether to sell open position when whale sells. Defaults to True."""
        return True

    def set_qualified_roster(self, roster: List[WhaleQualification]):
        """Optional hook to receive qualified whale metadata from data loader."""
        pass


class FixedAmountEntryStrategy(BaseStrategy):
    """
    Fixed Dollar Entry Strategy:
    Deploys a fixed dollar amount ($100 by default) per copy BUY signal.
    """
    def __init__(self, entry_usd: float = 100.0, name: Optional[str] = None):
        super().__init__(name or f"FixedEntry_${int(entry_usd)}")
        self.entry_usd = entry_usd

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None
        return round(self.entry_usd, 2)


class FixedProportionalStrategy(BaseStrategy):
    """Simple baseline strategy: allocates a fixed percentage of total portfolio per trade."""
    def __init__(self, fraction: float = 0.02, name: Optional[str] = None):
        pct = int(fraction * 100)
        super().__init__(name or f"FixedProportional_{pct}pct")
        self.fraction = fraction

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None
        intended = portfolio.initial_capital * self.fraction
        return round(intended, 2)


class GoldSniperStrategy(BaseStrategy):
    """
    High-Conviction Gold Snipers Only:
    1. Filters only top-tier Gold Snipers (win rate >= 80%, high historical PnL, no hedging).
    2. Filters out low-conviction/feeler trades: requires whale order size >= 70th percentile of whale's trade history.
    3. Conviction-weighted sizing: scales exponentially with trade conviction.
    """
    def __init__(self, min_conviction: float = 0.70, name: str = "HighConviction_GoldSnipers"):
        super().__init__(name)
        self.min_conviction = min_conviction
        self.gold_sniper_addresses: Set[str] = set()
        self.trailing_sizes: Dict[str, List[float]] = {}

    def set_qualified_roster(self, roster: List[WhaleQualification]):
        self.gold_sniper_addresses = {
            q.address.lower() for q in roster if q.tier == "gold_sniper" or q.win_rate_pct >= 80.0
        }

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None

        clean_whale = signal.whale_address.lower()
        if self.gold_sniper_addresses and clean_whale not in self.gold_sniper_addresses:
            return None  # Disqualify non-gold snipers

        sizes = self.trailing_sizes.setdefault(clean_whale, [])
        sizes.append(signal.whale_size_usd)
        if len(sizes) > 100:
            sizes.pop(0)

        # Require at least 2 trades to establish an empirical distribution
        if len(sizes) < 2:
            return None

        conviction = SleeveManager.calculate_conviction_percentile(signal.whale_size_usd, sizes)
        if conviction < self.min_conviction:
            return None  # Skip low-conviction feeler trades

        # Sizing scales with conviction: budget * (conviction ^ 1.5)
        budget = portfolio.sleeve_budgets.get(clean_whale, portfolio.config.initial_capital * portfolio.config.max_sleeve_fraction)
        sleeve_cash = portfolio.get_available_sleeve_cash(clean_whale)
        intended = budget * (conviction ** 1.5)
        return round(min(intended, sleeve_cash), 2)


class ConsensusConfirmationStrategy(BaseStrategy):
    """
    Consensus / Multi-Whale Confirmation Strategy:
    Requires 2 or more distinct qualified whales to buy the SAME outcome token on the SAME market
    within a confirmation time window (e.g. 24 hours).
    Signals from a single whale are tracked as pending; once confirmed by a 2nd whale,
    an aggressive high-conviction order is executed with cooldown protection.
    """
    def __init__(self, min_whales: int = 2, window_sec: float = 86400.0, name: str = "Consensus_2Whales_Confirm"):
        super().__init__(name)
        self.min_whales = min_whales
        self.window_sec = window_sec
        # (market_id, nonusdc_side) -> {whale_address: timestamp}
        self.pending_buys: Dict[Tuple[str, str], Dict[str, float]] = {}
        # Track confirmed and executed consensus keys with cooldown timestamp
        self.executed_consensus: Dict[Tuple[str, str], float] = {}

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None

        key = (signal.market_id, signal.nonusdc_side)
        curr_ts = float(signal.timestamp)

        # Enforce 6-hour cooldown on repeated consensus entries for the exact same market outcome
        last_exec = self.executed_consensus.get(key, 0.0)
        if curr_ts - last_exec < 21600.0:  # 6 hours
            return None

        whales_dict = self.pending_buys.setdefault(key, {})

        # Prune expired signals older than window_sec
        active_whales = {w: t for w, t in whales_dict.items() if curr_ts - t <= self.window_sec}
        active_whales[signal.whale_address.lower()] = curr_ts
        self.pending_buys[key] = active_whales

        # Check if consensus threshold is met
        distinct_whales = len(active_whales)
        if distinct_whales < self.min_whales:
            return None  # Awaiting 2nd whale confirmation

        self.executed_consensus[key] = curr_ts

        # Confirmed consensus: deploy 4% of portfolio capital per consensus signal
        intended = portfolio.initial_capital * 0.04
        return round(intended, 2)


class TopSharpeKellyStrategy(BaseStrategy):
    """
    Top Whales by Sharpe with Dynamic Fractional Kelly Sizing:
    1. Selects the Top 5 Whales ranked by Sharpe ratio.
    2. Sizes each trade using the Half-Kelly formula:
       f* = 0.5 * [(p * (b + 1) - 1) / b]
       where p is whale's empirical win rate, b is payoff odds: (1 - price) / price.
       If expected edge <= 0, trade is skipped (no negative EV bets).
    """
    def __init__(self, top_n: int = 5, name: str = "Top5_Whales_Sharpe_Kelly"):
        super().__init__(name)
        self.top_n = top_n
        self.top_whales: Set[str] = set()
        self.whale_win_rates: Dict[str, float] = {}

    def set_qualified_roster(self, roster: List[WhaleQualification]):
        # Sort roster by Sharpe ratio descending
        sorted_roster = sorted(roster, key=lambda q: (q.sharpe_ratio, q.win_rate_pct), reverse=True)
        top_list = sorted_roster[:self.top_n]
        self.top_whales = {q.address.lower() for q in top_list}
        self.whale_win_rates = {q.address.lower(): q.win_rate_pct / 100.0 for q in top_list}

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None

        clean_whale = signal.whale_address.lower()
        if self.top_whales and clean_whale not in self.top_whales:
            return None

        p = self.whale_win_rates.get(clean_whale, 0.70)
        price = max(0.02, min(0.98, signal.whale_price))
        b = (1.0 - price) / price  # Payoff odds: profit per dollar risked

        # Half-Kelly fraction
        edge = (p * (b + 1.0) - 1.0)
        if edge <= 0.0:
            return None  # Skip negative expected value trades

        kelly_f = 0.5 * (edge / max(0.01, b))
        safe_f = max(0.01, min(0.08, kelly_f))  # Clamp between 1% and 8% of portfolio

        intended = portfolio.initial_capital * safe_f
        return round(intended, 2)


class ResolutionHoldStrategy(BaseStrategy):
    """
    Resolution Hold ("Diamond Hands") Strategy:
    Ignores whale early exits / partial sells.
    Holds contracts until official market resolution to collect full $1.00 payout
    without paying intermediate exit taker fees or incurring spread slippage.
    """
    def __init__(self, fraction: float = 0.03, name: str = "Resolution_Hold_DiamondHands"):
        super().__init__(name)
        self.fraction = fraction

    def should_mirror_whale_exit(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> bool:
        return False  # Never exit on whale sell; hold strictly to market resolution

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None
        return round(portfolio.initial_capital * self.fraction, 2)


class WhaleExitMirroringStrategy(BaseStrategy):
    """
    Whale Exit Mirroring Strategy:
    Strictly mirrors whale exits whenever the whale sells on the orderbook.
    """
    def __init__(self, fraction: float = 0.03, name: str = "Whale_Exit_Mirroring"):
        super().__init__(name)
        self.fraction = fraction

    def should_mirror_whale_exit(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> bool:
        return True

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None
        return round(portfolio.initial_capital * self.fraction, 2)


class SleeveConvictionStrategy(BaseStrategy):
    """
    Baleen Conviction Percentile Sizing:
    Sizes each order by ranking the whale's trade size against their own trailing trade history.
    """
    def __init__(self, name: str = "Sleeve_Conviction_Only"):
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
    def __init__(self, ev_multiplier: float = 2.5, name: str = "FeeAware_EV_Gate_2.5x"):
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

        assumed_whale_edge = max(0.01, (0.70 - p)) if p < 0.70 else 0.03
        if assumed_whale_edge < min_required_edge:
            return None

        return base_size


class AntiConflictGatedStrategy(SleeveConvictionStrategy):
    """
    Anti-Conflict Gate Strategy:
    Disqualifies any whale that trades opposing mutually exclusive positions (token1 and token2 on the same market).
    """
    def __init__(self, max_conflict_tolerance: float = 0.15, name: str = "AntiConflict_Gated"):
        super().__init__(name=name)
        self.max_conflict_tolerance = max_conflict_tolerance
        self.whale_market_sides: Dict[str, Dict[str, Set[str]]] = {}
        self.disqualified_whales: Set[str] = set()

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        clean_whale = signal.whale_address.lower()
        if clean_whale in self.disqualified_whales:
            return None

        if signal.side.upper() == "BUY":
            m_dict = self.whale_market_sides.setdefault(clean_whale, {})
            m_key = signal.condition_id or signal.market_id
            sides = m_dict.setdefault(m_key, set())
            sides.add(signal.nonusdc_side)

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
    def __init__(self, ev_multiplier: float = 2.5, max_conflict_ratio: float = 0.15, name: str = "Baleen_Adaptive_Production"):
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
