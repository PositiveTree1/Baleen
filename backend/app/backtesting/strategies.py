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
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from app.backtesting.models import TradeSignal, ClosedTrade, WhaleQualification
from app.backtesting.portfolio import SimulatedPortfolio
from app.sizing.sleeve_manager import SleeveManager
from app.sizing.dynamic_sizer import size_trade, SizingResult
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

    def on_trade_signal(self, signal: TradeSignal):
        """Optional hook called on each incoming chronological trade signal in the event stream."""
        pass

    def on_market_resolved(
        self,
        market_id: str,
        winning_token: Optional[str],
        resolution_timestamp: float,
        p1_payout: Optional[float] = None,
        p2_payout: Optional[float] = None
    ):
        """Optional hook called when a market reaches resolution."""
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


@dataclass
class WhalePositionTracker:
    shares: float
    cost_basis: float
    avg_price: float
    last_price: float
    market_id: str
    outcome_token: str


class BaleenDynamicSizerStrategy(BaseStrategy):
    """
    Authentic Baleen Production Dynamic Sizer Strategy (§5 Dynamic Sizer):
    Accurately tracks each whale's net worth right before each trade point:
      whale_net_worth = initial_net_worth + cumulative_realized_pnl + open_position_equity
    and executes size_trade(user_balance, risk_profile, n_active, whale_trade_value, whale_portfolio_value).
    Supports optional anti-conflict gating to filter out whales betting opposing tokens on the same market.
    """
    def __init__(
        self,
        risk_profile: str = "balanced",
        initial_whale_net_worth: float = 50000.0,
        enable_anti_conflict: bool = False,
        max_conflict_tolerance: float = 0.15,
        min_order_usd: float = 1.0,
        name: Optional[str] = None
    ):
        default_name = "Baleen_DynamicSizer_AntiConflict" if enable_anti_conflict else "Baleen_DynamicSizer_NetWorth"
        super().__init__(name or default_name)
        self.risk_profile = risk_profile
        self.default_whale_net_worth = initial_whale_net_worth
        self.enable_anti_conflict = enable_anti_conflict
        self.max_conflict_tolerance = max_conflict_tolerance
        self.min_order_usd = min_order_usd

        # Whale Accounting State
        self.whale_initial_net_worth: Dict[str, float] = {}
        self.whale_realized_pnl: Dict[str, float] = {}
        self.whale_open_positions: Dict[str, Dict[Tuple[str, str], WhalePositionTracker]] = {}
        self.latest_prices: Dict[Tuple[str, str], float] = {}

        # Anti-Conflict State
        self.whale_market_sides: Dict[str, Dict[str, Set[str]]] = {}
        self.disqualified_whales: Set[str] = set()
        self.active_roster_count: int = 10

    def set_qualified_roster(self, roster: List[WhaleQualification]):
        self.active_roster_count = max(1, len(roster))
        for q in roster:
            clean = q.address.lower()
            base_nw = max(self.default_whale_net_worth, float(q.realized_pnl)) if q.realized_pnl > 0 else self.default_whale_net_worth
            self.whale_initial_net_worth[clean] = base_nw
            self.whale_realized_pnl.setdefault(clean, 0.0)
            self.whale_open_positions.setdefault(clean, {})

    def get_whale_net_worth(self, whale_address: str) -> float:
        """
        Calculates whale's net worth right before the trade point:
        initial_net_worth + cumulative_realized_pnl + open_position_unrealized_pnl
        where open_position_unrealized_pnl = sum(pos.shares * curr_p - pos.cost_basis)
        """
        clean = whale_address.lower()
        base = self.whale_initial_net_worth.get(clean, self.default_whale_net_worth)
        realized = self.whale_realized_pnl.get(clean, 0.0)

        unrealized_pnl = 0.0
        positions = self.whale_open_positions.get(clean, {})
        for key, pos in positions.items():
            curr_p = self.latest_prices.get(key, pos.last_price or pos.avg_price)
            curr_val = pos.shares * curr_p
            unrealized_pnl += (curr_val - pos.cost_basis)

        net_worth = base + realized + unrealized_pnl
        return max(1000.0, net_worth)

    def on_trade_signal(self, signal: TradeSignal):
        """
        Processes incoming trade signals to keep whale accounting & latest prices fully updated.
        """
        key = (signal.market_id, signal.nonusdc_side)
        self.latest_prices[key] = signal.whale_price

        if signal.side.upper() == "SELL":
            self._record_whale_sell(signal)

    def _record_whale_buy(self, signal: TradeSignal):
        """Updates whale open positions on BUY."""
        clean_w = signal.whale_address.lower()
        positions = self.whale_open_positions.setdefault(clean_w, {})
        key = (signal.market_id, signal.nonusdc_side)

        price = max(0.001, signal.whale_price)
        shares_added = signal.whale_shares if signal.whale_shares > 0 else (signal.whale_size_usd / price)
        cost_added = signal.whale_size_usd

        if key in positions:
            pos = positions[key]
            new_shares = pos.shares + shares_added
            new_cost = pos.cost_basis + cost_added
            pos.avg_price = new_cost / new_shares if new_shares > 0 else price
            pos.shares = new_shares
            pos.cost_basis = new_cost
            pos.last_price = price
        else:
            positions[key] = WhalePositionTracker(
                shares=shares_added,
                cost_basis=cost_added,
                avg_price=price,
                last_price=price,
                market_id=signal.market_id,
                outcome_token=signal.nonusdc_side
            )

    def _record_whale_sell(self, signal: TradeSignal):
        """Updates whale open positions and realizes PnL on SELL."""
        clean_w = signal.whale_address.lower()
        positions = self.whale_open_positions.setdefault(clean_w, {})
        key = (signal.market_id, signal.nonusdc_side)

        if key not in positions:
            return

        pos = positions[key]
        price = max(0.001, signal.whale_price)
        shares_sold = signal.whale_shares if signal.whale_shares > 0 else (signal.whale_size_usd / price)
        shares_to_close = min(pos.shares, shares_sold)

        if shares_to_close <= 0:
            return

        fraction = shares_to_close / pos.shares if pos.shares > 0 else 1.0
        cost_sold = pos.cost_basis * fraction
        proceeds = shares_to_close * price
        realized_gain = proceeds - cost_sold

        self.whale_realized_pnl[clean_w] = self.whale_realized_pnl.get(clean_w, 0.0) + realized_gain
        pos.shares -= shares_to_close
        pos.cost_basis -= cost_sold
        pos.last_price = price

        if pos.shares <= 0.001:
            del positions[key]

    def on_market_resolved(
        self,
        market_id: str,
        winning_token: Optional[str],
        resolution_timestamp: float,
        p1_payout: Optional[float] = None,
        p2_payout: Optional[float] = None
    ):
        """Settles whale open positions upon market resolution."""
        for clean_w, positions in self.whale_open_positions.items():
            matching_keys = [k for k in list(positions.keys()) if k[0] == market_id]
            for key in matching_keys:
                pos = positions.pop(key)
                if p1_payout is not None and p2_payout is not None:
                    payout_price = p1_payout if pos.outcome_token == "token1" else p2_payout
                elif winning_token:
                    payout_price = 1.00 if pos.outcome_token == winning_token else 0.00
                else:
                    payout_price = 0.50

                gross_proceeds = pos.shares * payout_price
                realized = gross_proceeds - pos.cost_basis
                self.whale_realized_pnl[clean_w] = self.whale_realized_pnl.get(clean_w, 0.0) + realized

    def evaluate_signal(self, signal: TradeSignal, portfolio: SimulatedPortfolio) -> Optional[float]:
        if signal.side.upper() != "BUY":
            return None

        clean_w = signal.whale_address.lower()

        # 1. Anti-Conflict Gating (if enabled)
        if self.enable_anti_conflict:
            if clean_w in self.disqualified_whales:
                self._record_whale_buy(signal)
                return None

            m_dict = self.whale_market_sides.setdefault(clean_w, {})
            m_key = signal.condition_id or signal.market_id
            sides = m_dict.setdefault(m_key, set())

            # Skip opposing trades on the same market (hedging prevention)
            if len(sides) > 0 and signal.nonusdc_side not in sides:
                sides.add(signal.nonusdc_side)
                conflicts = sum(1 for s in m_dict.values() if len(s) > 1)
                total_mkts = max(1, len(m_dict))
                if (conflicts / total_mkts) > self.max_conflict_tolerance:
                    self.disqualified_whales.add(clean_w)
                self._record_whale_buy(signal)
                return None

            sides.add(signal.nonusdc_side)

            conflicts = sum(1 for s in m_dict.values() if len(s) > 1)
            total_mkts = max(1, len(m_dict))
            if conflicts >= 1 and (conflicts / total_mkts) > self.max_conflict_tolerance:
                self.disqualified_whales.add(clean_w)
                self._record_whale_buy(signal)
                return None

        # 2. Track latest price for the token
        key = (signal.market_id, signal.nonusdc_side)
        self.latest_prices[key] = signal.whale_price

        # 3. Calculate Whale Net Worth right before the trade point
        whale_nw = self.get_whale_net_worth(clean_w)
        # Ensure portfolio value is at least the trade value (as in live poller max(1000.0, whale_port_val))
        whale_portfolio_val = max(1000.0, signal.whale_size_usd, whale_nw)

        # 4. User balance and active wallets
        # In Baleen, user_balance = sandbox_balance_usd = initial_capital + realized_pnl
        user_balance = max(0.0, portfolio.initial_capital + sum(t.net_pnl for t in portfolio.closed_trades))
        n_active = max(1, len(portfolio.sleeve_budgets) if portfolio.sleeve_budgets else self.active_roster_count)

        # 5. Call Baleen Authentic §5 Dynamic Sizer
        sizing_res = size_trade(
            user_balance=user_balance,
            risk_profile=self.risk_profile,
            n_active=n_active,
            whale_trade_value=signal.whale_size_usd,
            whale_portfolio_value=whale_portfolio_val,
            min_order_usd=self.min_order_usd
        )

        if sizing_res.status != "SUCCESS" or sizing_res.value <= 0:
            # Still record whale buy to maintain accurate future net worth tracking
            self._record_whale_buy(signal)
            return None

        # 6. Check available cash & sleeve limits
        sleeve_cash = portfolio.get_available_sleeve_cash(clean_w)
        final_size = min(sizing_res.value, portfolio.cash, sleeve_cash)

        if final_size < self.min_order_usd:
            self._record_whale_buy(signal)
            return None

        # Record whale buy state for subsequent net worth calculations
        self._record_whale_buy(signal)
        return round(final_size, 2)

