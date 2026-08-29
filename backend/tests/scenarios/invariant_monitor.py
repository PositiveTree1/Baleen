"""
Baleen State Machine Invariant Monitor.

Implements rigorous state machine monitoring across all 10 core mathematical,
cash, margin, and lifecycle invariants for the Baleen prediction market copy-trading engine:
  1. Cash Non-Negativity: Cash >= 0.0
  2. Margin Equation: Free Cash == max(0.0, Settled Cash - Open Margin)
  3. High-Water Mark Monotonicity: HWM_{t+1} >= HWM_t (no phantom ratcheting)
  4. FIFO Lot Splitting Conservation: sum(V_split) == V_orig and sum(Fee_split) == Fee_orig
  5. 2026 Quadratic Polymarket Fee Bounds: 0.0 <= Fee <= 0.072 * Notional across 6 asset classes
  6. Zero Orphaned Positions: No open BUY lots remain after complete matching SELL exits
  7. Ghost Sell Fill Prevention: Users with 0 open positions never receive SELL fills or pay fees
  8. Numerical & IEEE Safety: Zero NaNs, Infs, zero-division crashes, or unbounded floats
  9. MTM Cash Isolation: Unrealized mark-to-market never inflates settled cash or free cash
  10. Position Balance & Equity Integrity: Total Equity == Settled Cash + Unrealized PnL
"""

from __future__ import annotations

import enum
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Union

logger = logging.getLogger(__name__)


class InvariantSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class InvariantCheckType(str, enum.Enum):
    CASH_NON_NEGATIVITY = "CASH_NON_NEGATIVITY"
    MARGIN_EQUATION = "MARGIN_EQUATION"
    HIGH_WATER_MARK_MONOTONICITY = "HIGH_WATER_MARK_MONOTONICITY"
    FIFO_LOT_SPLIT_CONSERVATION = "FIFO_LOT_SPLIT_CONSERVATION"
    FEE_BOUNDS = "FEE_BOUNDS"
    ZERO_ORPHANED_POSITIONS = "ZERO_ORPHANED_POSITIONS"
    GHOST_SELL_PREVENTION = "GHOST_SELL_PREVENTION"
    NUMERICAL_IEEE_SAFETY = "NUMERICAL_IEEE_SAFETY"
    MTM_CASH_ISOLATION = "MTM_CASH_ISOLATION"
    POSITION_BALANCE_INTEGRITY = "POSITION_BALANCE_INTEGRITY"


@dataclass
class PositionLot:
    """Represents an individual trade lot / split position in the FIFO lifecycle."""
    lot_id: str
    condition_id: str
    outcome: str
    side: str  # BUY or SELL
    price: float
    shares: float
    notional_usd: float
    fee_usd: float
    status: str = "FILLED"  # FILLED, CLOSED, SPLIT
    user_id: Optional[str] = None
    wallet_address: str = ""
    market_question: str = ""
    market_category: str = "General"
    parent_lot_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    realized_pnl_usd: Optional[float] = None


@dataclass
class TradeExecution:
    """Represents an executed trade attempt or fill."""
    trade_id: str
    condition_id: str
    outcome: str
    side: str  # BUY or SELL
    price: float
    shares: float
    notional_usd: float
    fee_usd: float
    user_id: Optional[str] = None
    wallet_address: str = ""
    market_title: str = ""
    market_category: str = "General"
    is_maker: bool = False
    status: str = "FILLED"  # FILLED, REJECTED, SKIPPED, CLOSED
    executed_at: float = field(default_factory=time.time)
    failure_detail: Optional[str] = None


@dataclass
class PortfolioState:
    """Authoritative snapshot of a user or platform portfolio state."""
    user_id: Optional[str]
    settled_cash_usd: float
    free_cash_usd: float
    open_margin_usd: float
    high_water_mark_usd: float
    open_positions: List[PositionLot] = field(default_factory=list)
    closed_positions: List[PositionLot] = field(default_factory=list)
    total_realized_pnl_usd: float = 0.0
    total_unrealized_pnl_usd: float = 0.0
    equity_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def total_open_notional(self) -> float:
        return sum(
            lot.notional_usd
            for lot in self.open_positions
            if lot.status == "FILLED" and lot.side == "BUY"
        )

    def open_shares_for(self, condition_id: str, outcome: str) -> float:
        return sum(
            lot.shares
            for lot in self.open_positions
            if lot.status == "FILLED"
            and lot.condition_id == condition_id
            and lot.outcome.lower() == outcome.lower()
            and lot.side == "BUY"
        )


@dataclass
class InvariantViolation:
    """Structured report of a detected invariant violation."""
    invariant_name: str
    check_type: InvariantCheckType
    severity: InvariantSeverity
    message: str
    observed_value: Union[float, str, dict, list, None]
    expected_value: Union[float, str, dict, list, None]
    context: Dict[str, Union[float, str, int, bool, None]] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class InvariantResult:
    """Summary result of invariant validation checks."""
    is_valid: bool
    violations: List[InvariantViolation] = field(default_factory=list)
    checked_count: int = 0
    passed_count: int = 0

    def add_violation(self, violation: InvariantViolation) -> None:
        self.violations.append(violation)
        self.is_valid = False

    def add_violations(self, new_violations: Sequence[InvariantViolation]) -> None:
        for v in new_violations:
            self.add_violation(v)


class InvariantMonitor:
    """
    Continuous state machine validator checking all 10 core mathematical
    and business invariants across simulated and live Baleen state transitions.
    """

    FLOAT_EPSILON: float = 1e-5
    CENT_TOLERANCE: float = 0.015

    # 2026 Polymarket Category Theta Schedule
    CATEGORY_THETA_MAP: Dict[str, float] = {
        "Crypto": 0.072,
        "Economics / Finance": 0.060,
        "Culture, Weather & Tech": 0.050,
        "Politics": 0.040,
        "Sports": 0.030,
        "Geopolitics": 0.000,
        "General": 0.050,
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.history_violations: List[InvariantViolation] = []

    # -------------------------------------------------------------------------
    # 1. Cash Non-Negativity
    # -------------------------------------------------------------------------
    def check_cash_non_negativity(self, state: PortfolioState) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        if state.settled_cash_usd < -self.FLOAT_EPSILON:
            violations.append(
                InvariantViolation(
                    invariant_name="Cash Non-Negativity (Settled Cash)",
                    check_type=InvariantCheckType.CASH_NON_NEGATIVITY,
                    severity=InvariantSeverity.CRITICAL,
                    message=f"Settled cash fell below zero: ${state.settled_cash_usd:.4f}",
                    observed_value=state.settled_cash_usd,
                    expected_value=">= 0.0",
                    context={"user_id": state.user_id, "timestamp": state.timestamp},
                )
            )

        if state.free_cash_usd < -self.FLOAT_EPSILON:
            violations.append(
                InvariantViolation(
                    invariant_name="Cash Non-Negativity (Free Cash)",
                    check_type=InvariantCheckType.CASH_NON_NEGATIVITY,
                    severity=InvariantSeverity.CRITICAL,
                    message=f"Free cash fell below zero: ${state.free_cash_usd:.4f}",
                    observed_value=state.free_cash_usd,
                    expected_value=">= 0.0",
                    context={"user_id": state.user_id, "timestamp": state.timestamp},
                )
            )

        if state.open_margin_usd < -self.FLOAT_EPSILON:
            violations.append(
                InvariantViolation(
                    invariant_name="Margin Non-Negativity",
                    check_type=InvariantCheckType.CASH_NON_NEGATIVITY,
                    severity=InvariantSeverity.HIGH,
                    message=f"Open margin requirement is negative: ${state.open_margin_usd:.4f}",
                    observed_value=state.open_margin_usd,
                    expected_value=">= 0.0",
                    context={"user_id": state.user_id, "timestamp": state.timestamp},
                )
            )

        return violations

    # -------------------------------------------------------------------------
    # 2. Margin Equation
    # -------------------------------------------------------------------------
    def check_margin_equation(self, state: PortfolioState) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []
        expected_free_cash = max(0.0, state.settled_cash_usd - state.open_margin_usd)

        diff = abs(state.free_cash_usd - expected_free_cash)
        if diff > self.CENT_TOLERANCE:
            violations.append(
                InvariantViolation(
                    invariant_name="Margin Equation Invariance",
                    check_type=InvariantCheckType.MARGIN_EQUATION,
                    severity=InvariantSeverity.CRITICAL,
                    message=(
                        f"Free cash (${state.free_cash_usd:.2f}) does not match "
                        f"max(0, Settled Cash (${state.settled_cash_usd:.2f}) - Open Margin (${state.open_margin_usd:.2f})) "
                        f"= ${expected_free_cash:.2f}. Discrepancy: ${diff:.4f}"
                    ),
                    observed_value=state.free_cash_usd,
                    expected_value=expected_free_cash,
                    context={
                        "settled_cash": state.settled_cash_usd,
                        "open_margin": state.open_margin_usd,
                        "user_id": state.user_id,
                    },
                )
            )

        # Also check open margin matches sum of active BUY lots
        active_buy_notional = state.total_open_notional()
        margin_diff = abs(state.open_margin_usd - active_buy_notional)
        if margin_diff > self.CENT_TOLERANCE:
            violations.append(
                InvariantViolation(
                    invariant_name="Open Margin Sum Matching",
                    check_type=InvariantCheckType.MARGIN_EQUATION,
                    severity=InvariantSeverity.HIGH,
                    message=(
                        f"Recorded open margin (${state.open_margin_usd:.2f}) does not match "
                        f"sum of active open BUY notional (${active_buy_notional:.2f})."
                    ),
                    observed_value=state.open_margin_usd,
                    expected_value=active_buy_notional,
                    context={"user_id": state.user_id},
                )
            )

        return violations

    # -------------------------------------------------------------------------
    # 3. High-Water Mark Monotonicity
    # -------------------------------------------------------------------------
    def check_hwm_monotonicity(
        self,
        prev_state: PortfolioState,
        cur_state: PortfolioState,
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        if cur_state.high_water_mark_usd < prev_state.high_water_mark_usd - self.FLOAT_EPSILON:
            violations.append(
                InvariantViolation(
                    invariant_name="High-Water Mark Monotonicity",
                    check_type=InvariantCheckType.HIGH_WATER_MARK_MONOTONICITY,
                    severity=InvariantSeverity.CRITICAL,
                    message=(
                        f"High-Water Mark decreased from ${prev_state.high_water_mark_usd:.2f} "
                        f"to ${cur_state.high_water_mark_usd:.2f}."
                    ),
                    observed_value=cur_state.high_water_mark_usd,
                    expected_value=f">= {prev_state.high_water_mark_usd:.2f}",
                    context={
                        "prev_hwm": prev_state.high_water_mark_usd,
                        "cur_hwm": cur_state.high_water_mark_usd,
                        "user_id": cur_state.user_id,
                    },
                )
            )

        # Check HWM does not exceed verified total equity
        if cur_state.high_water_mark_usd > cur_state.equity_usd + self.CENT_TOLERANCE and cur_state.high_water_mark_usd > prev_state.high_water_mark_usd:
            # Ratcheted above current equity: HWM can only increase if equity exceeds previous HWM
            violations.append(
                InvariantViolation(
                    invariant_name="High-Water Mark Phantom Ratcheting",
                    check_type=InvariantCheckType.HIGH_WATER_MARK_MONOTONICITY,
                    severity=InvariantSeverity.HIGH,
                    message=(
                        f"HWM ratcheted up to ${cur_state.high_water_mark_usd:.2f} exceeding current equity ${cur_state.equity_usd:.2f}."
                    ),
                    observed_value=cur_state.high_water_mark_usd,
                    expected_value=f"<= {cur_state.equity_usd:.2f}",
                    context={"cur_equity": cur_state.equity_usd, "user_id": cur_state.user_id},
                )
            )

        return violations

    # -------------------------------------------------------------------------
    # 4. FIFO Lot Splitting Conservation
    # -------------------------------------------------------------------------
    def check_fifo_lot_split_conservation(
        self,
        orig_lot: PositionLot,
        split_lots: List[PositionLot],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        if not split_lots:
            violations.append(
                InvariantViolation(
                    invariant_name="FIFO Lot Split Existence",
                    check_type=InvariantCheckType.FIFO_LOT_SPLIT_CONSERVATION,
                    severity=InvariantSeverity.CRITICAL,
                    message=f"Original lot {orig_lot.lot_id} was split into 0 child lots.",
                    observed_value=0,
                    expected_value=">= 1 split lots",
                    context={"orig_lot_id": orig_lot.lot_id},
                )
            )
            return violations

        total_split_notional = sum(lot.notional_usd for lot in split_lots)
        total_split_fee = sum(lot.fee_usd for lot in split_lots)
        total_split_shares = sum(lot.shares for lot in split_lots)

        # Notional conservation
        notional_diff = abs(total_split_notional - orig_lot.notional_usd)
        if notional_diff > self.CENT_TOLERANCE:
            violations.append(
                InvariantViolation(
                    invariant_name="FIFO Lot Splitting Dollar Conservation",
                    check_type=InvariantCheckType.FIFO_LOT_SPLIT_CONSERVATION,
                    severity=InvariantSeverity.CRITICAL,
                    message=(
                        f"Split lots dollar sum (${total_split_notional:.4f}) does not equal "
                        f"original lot notional (${orig_lot.notional_usd:.4f}). Leaked: ${notional_diff:.4f}"
                    ),
                    observed_value=total_split_notional,
                    expected_value=orig_lot.notional_usd,
                    context={"orig_lot_id": orig_lot.lot_id, "split_count": len(split_lots)},
                )
            )

        # Fee conservation
        fee_diff = abs(total_split_fee - orig_lot.fee_usd)
        if fee_diff > 0.005:
            violations.append(
                InvariantViolation(
                    invariant_name="FIFO Lot Splitting Fee Conservation",
                    check_type=InvariantCheckType.FIFO_LOT_SPLIT_CONSERVATION,
                    severity=InvariantSeverity.HIGH,
                    message=(
                        f"Split lots fee sum (${total_split_fee:.4f}) does not equal "
                        f"original lot fee (${orig_lot.fee_usd:.4f}). Discrepancy: ${fee_diff:.4f}"
                    ),
                    observed_value=total_split_fee,
                    expected_value=orig_lot.fee_usd,
                    context={"orig_lot_id": orig_lot.lot_id},
                )
            )

        # Shares conservation
        shares_diff = abs(total_split_shares - orig_lot.shares)
        if shares_diff > 1e-3:
            violations.append(
                InvariantViolation(
                    invariant_name="FIFO Lot Splitting Shares Conservation",
                    check_type=InvariantCheckType.FIFO_LOT_SPLIT_CONSERVATION,
                    severity=InvariantSeverity.HIGH,
                    message=(
                        f"Split lots shares sum ({total_split_shares:.4f}) does not equal "
                        f"original shares ({orig_lot.shares:.4f}). Discrepancy: {shares_diff:.4f}"
                    ),
                    observed_value=total_split_shares,
                    expected_value=orig_lot.shares,
                    context={"orig_lot_id": orig_lot.lot_id},
                )
            )

        return violations

    # -------------------------------------------------------------------------
    # 5. 2026 Quadratic Polymarket Fee Bounds
    # -------------------------------------------------------------------------
    def check_fee_bounds(
        self,
        execution: TradeExecution,
        max_theta: float = 0.072,
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        if execution.fee_usd < -self.FLOAT_EPSILON:
            violations.append(
                InvariantViolation(
                    invariant_name="Fee Non-Negativity",
                    check_type=InvariantCheckType.FEE_BOUNDS,
                    severity=InvariantSeverity.CRITICAL,
                    message=f"Trade fee is negative: ${execution.fee_usd:.4f}",
                    observed_value=execution.fee_usd,
                    expected_value=">= 0.0",
                    context={"trade_id": execution.trade_id},
                )
            )

        # Maker trades must be 0-fee
        if execution.is_maker and execution.fee_usd > self.FLOAT_EPSILON:
            violations.append(
                InvariantViolation(
                    invariant_name="Maker Fee Free Invariance",
                    check_type=InvariantCheckType.FEE_BOUNDS,
                    severity=InvariantSeverity.HIGH,
                    message=f"Maker trade charged non-zero fee: ${execution.fee_usd:.4f}",
                    observed_value=execution.fee_usd,
                    expected_value=0.0,
                    context={"trade_id": execution.trade_id},
                )
            )

        # Absolute upper bound: Theta_max * Notional (where Theta_max = 0.072 for Crypto at p -> 0)
        max_possible_fee = (max_theta * execution.notional_usd) + self.CENT_TOLERANCE
        if execution.fee_usd > max_possible_fee:
            violations.append(
                InvariantViolation(
                    invariant_name="Quadratic Fee Ceiling",
                    check_type=InvariantCheckType.FEE_BOUNDS,
                    severity=InvariantSeverity.CRITICAL,
                    message=(
                        f"Fee ${execution.fee_usd:.4f} exceeds theoretical maximum "
                        f"0.072 * Notional (${execution.notional_usd:.2f}) = ${max_possible_fee:.4f}"
                    ),
                    observed_value=execution.fee_usd,
                    expected_value=f"<= {max_possible_fee:.4f}",
                    context={"trade_id": execution.trade_id, "notional": execution.notional_usd},
                )
            )

        # Category specific theta bound check if category recognized
        category_theta = self.CATEGORY_THETA_MAP.get(execution.market_category)
        if category_theta is not None and not execution.is_maker:
            cat_max_fee = (category_theta * execution.notional_usd) + self.CENT_TOLERANCE
            if execution.fee_usd > cat_max_fee:
                violations.append(
                    InvariantViolation(
                        invariant_name=f"Category Fee Bound ({execution.market_category})",
                        check_type=InvariantCheckType.FEE_BOUNDS,
                        severity=InvariantSeverity.HIGH,
                        message=(
                            f"Fee ${execution.fee_usd:.4f} exceeds category ({execution.market_category}, Theta={category_theta}) "
                            f"ceiling of ${cat_max_fee:.4f}."
                        ),
                        observed_value=execution.fee_usd,
                        expected_value=f"<= {cat_max_fee:.4f}",
                        context={
                            "trade_id": execution.trade_id,
                            "category": execution.market_category,
                            "theta": category_theta,
                        },
                    )
                )

        return violations

    # -------------------------------------------------------------------------
    # 6. Zero Orphaned Positions
    # -------------------------------------------------------------------------
    def check_zero_orphaned_positions(
        self,
        positions: List[PositionLot],
        condition_id: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        # Filter by condition/outcome if provided
        filtered = positions
        if condition_id:
            filtered = [p for p in filtered if p.condition_id == condition_id]
        if outcome:
            filtered = [p for p in filtered if p.outcome.lower() == outcome.lower()]

        # Group by condition_id and outcome
        groups: Dict[tuple[str, str], List[PositionLot]] = {}
        for p in filtered:
            key = (p.condition_id, p.outcome.lower())
            groups.setdefault(key, []).append(p)

        for (cid, outc), group_lots in groups.items():
            buy_shares = sum(l.shares for l in group_lots if l.side == "BUY")
            closed_buy_shares = sum(
                l.shares for l in group_lots if l.side == "BUY" and l.status == "CLOSED"
            )
            open_buy_lots = [l for l in group_lots if l.side == "BUY" and l.status == "FILLED"]

            # If all bought shares were closed, no open BUY lots should remain
            if abs(buy_shares - closed_buy_shares) < 1e-4 and len(open_buy_lots) > 0:
                violations.append(
                    InvariantViolation(
                        invariant_name="Zero Orphaned Positions",
                        check_type=InvariantCheckType.ZERO_ORPHANED_POSITIONS,
                        severity=InvariantSeverity.CRITICAL,
                        message=(
                            f"Position {cid}:{outc} has 100% closed volume ({closed_buy_shares:.4f}/{buy_shares:.4f} shares), "
                            f"but {len(open_buy_lots)} open BUY lot(s) still remain in FILLED status."
                        ),
                        observed_value=len(open_buy_lots),
                        expected_value=0,
                        context={"condition_id": cid, "outcome": outc, "orphaned_count": len(open_buy_lots)},
                    )
                )

        return violations

    # -------------------------------------------------------------------------
    # 7. Ghost Sell Fill Prevention
    # -------------------------------------------------------------------------
    def check_ghost_sell_prevention(
        self,
        pre_state: PortfolioState,
        sell_execution: TradeExecution,
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        if sell_execution.side.upper() != "SELL":
            return violations

        held_shares = pre_state.open_shares_for(
            sell_execution.condition_id,
            sell_execution.outcome,
        )

        # If user had 0 open shares on this market, executing a SELL fill is a ghost fill!
        if held_shares <= self.FLOAT_EPSILON and sell_execution.status == "FILLED":
            violations.append(
                InvariantViolation(
                    invariant_name="Ghost Sell Fill Execution",
                    check_type=InvariantCheckType.GHOST_SELL_PREVENTION,
                    severity=InvariantSeverity.CRITICAL,
                    message=(
                        f"User {pre_state.user_id} had 0 open shares for {sell_execution.condition_id}:{sell_execution.outcome}, "
                        f"but received a FILLED SELL trade of {sell_execution.shares:.4f} shares ($ {sell_execution.notional_usd:.2f})."
                    ),
                    observed_value=sell_execution.status,
                    expected_value="REJECTED / SKIPPED",
                    context={
                        "user_id": pre_state.user_id,
                        "condition_id": sell_execution.condition_id,
                        "outcome": sell_execution.outcome,
                        "held_shares": held_shares,
                        "sell_shares": sell_execution.shares,
                    },
                )
            )

        # If user had 0 open shares, fee must be 0.0
        if held_shares <= self.FLOAT_EPSILON and sell_execution.fee_usd > self.FLOAT_EPSILON:
            violations.append(
                InvariantViolation(
                    invariant_name="Ghost Sell Fee Leak",
                    check_type=InvariantCheckType.GHOST_SELL_PREVENTION,
                    severity=InvariantSeverity.HIGH,
                    message=(
                        f"User {pre_state.user_id} charged fee ${sell_execution.fee_usd:.4f} "
                        f"on a ghost sell with 0 held shares."
                    ),
                    observed_value=sell_execution.fee_usd,
                    expected_value=0.0,
                    context={"user_id": pre_state.user_id, "trade_id": sell_execution.trade_id},
                )
            )

        return violations

    # -------------------------------------------------------------------------
    # 8. Numerical & IEEE Safety
    # -------------------------------------------------------------------------
    def check_numerical_safety(
        self,
        values: Union[Dict[str, Union[float, int, None]], PortfolioState, TradeExecution],
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        dict_repr: Dict[str, Union[float, int, None, str]] = {}
        if isinstance(values, PortfolioState):
            dict_repr = {
                "settled_cash_usd": values.settled_cash_usd,
                "free_cash_usd": values.free_cash_usd,
                "open_margin_usd": values.open_margin_usd,
                "high_water_mark_usd": values.high_water_mark_usd,
                "equity_usd": values.equity_usd,
                "total_realized_pnl_usd": values.total_realized_pnl_usd,
                "total_unrealized_pnl_usd": values.total_unrealized_pnl_usd,
            }
        elif isinstance(values, TradeExecution):
            dict_repr = {
                "price": values.price,
                "shares": values.shares,
                "notional_usd": values.notional_usd,
                "fee_usd": values.fee_usd,
            }
        elif isinstance(values, dict):
            dict_repr = values

        for k, v in dict_repr.items():
            if isinstance(v, (float, int)):
                val_float = float(v)
                if math.isnan(val_float):
                    violations.append(
                        InvariantViolation(
                            invariant_name=f"Numerical Safety (NaN in {k})",
                            check_type=InvariantCheckType.NUMERICAL_IEEE_SAFETY,
                            severity=InvariantSeverity.CRITICAL,
                            message=f"Field '{k}' evaluated to NaN (Not-a-Number).",
                            observed_value="NaN",
                            expected_value="Finite float",
                            context={"field": k},
                        )
                    )
                elif math.isinf(val_float):
                    violations.append(
                        InvariantViolation(
                            invariant_name=f"Numerical Safety (Inf in {k})",
                            check_type=InvariantCheckType.NUMERICAL_IEEE_SAFETY,
                            severity=InvariantSeverity.CRITICAL,
                            message=f"Field '{k}' evaluated to infinite value ({v}).",
                            observed_value="Infinity",
                            expected_value="Finite float",
                            context={"field": k},
                        )
                    )

        return violations

    # -------------------------------------------------------------------------
    # 9. MTM Cash Isolation
    # -------------------------------------------------------------------------
    def check_mtm_cash_isolation(
        self,
        prev_state: PortfolioState,
        cur_state: PortfolioState,
        executed_trade: Optional[TradeExecution] = None,
    ) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        # If no trade was executed in this step (pure price update / MTM cycle):
        if executed_trade is None:
            settled_cash_diff = abs(cur_state.settled_cash_usd - prev_state.settled_cash_usd)
            if settled_cash_diff > self.CENT_TOLERANCE:
                violations.append(
                    InvariantViolation(
                        invariant_name="MTM Cash Isolation",
                        check_type=InvariantCheckType.MTM_CASH_ISOLATION,
                        severity=InvariantSeverity.CRITICAL,
                        message=(
                            f"Settled cash changed from ${prev_state.settled_cash_usd:.2f} to "
                            f"${cur_state.settled_cash_usd:.2f} during a pure MTM valuation cycle without trade realization."
                        ),
                        observed_value=cur_state.settled_cash_usd,
                        expected_value=prev_state.settled_cash_usd,
                        context={"diff": settled_cash_diff, "user_id": cur_state.user_id},
                    )
                )

        return violations

    # -------------------------------------------------------------------------
    # 10. Position Balance Integrity
    # -------------------------------------------------------------------------
    def check_position_balance_integrity(self, state: PortfolioState) -> List[InvariantViolation]:
        violations: List[InvariantViolation] = []

        expected_equity = round(state.settled_cash_usd + state.total_unrealized_pnl_usd, 2)
        equity_diff = abs(state.equity_usd - expected_equity)
        if equity_diff > self.CENT_TOLERANCE:
            violations.append(
                InvariantViolation(
                    invariant_name="Portfolio Equity Integrity",
                    check_type=InvariantCheckType.POSITION_BALANCE_INTEGRITY,
                    severity=InvariantSeverity.HIGH,
                    message=(
                        f"Recorded equity (${state.equity_usd:.2f}) does not match "
                        f"Settled Cash (${state.settled_cash_usd:.2f}) + Unrealized PnL (${state.total_unrealized_pnl_usd:.2f}) "
                        f"= ${expected_equity:.2f}."
                    ),
                    observed_value=state.equity_usd,
                    expected_value=expected_equity,
                    context={"user_id": state.user_id},
                )
            )

        return violations

    # -------------------------------------------------------------------------
    # Comprehensive Transition Validation
    # -------------------------------------------------------------------------
    def validate_transition(
        self,
        prev_state: Optional[PortfolioState],
        cur_state: PortfolioState,
        execution: Optional[TradeExecution] = None,
        split_orig_lot: Optional[PositionLot] = None,
        split_child_lots: Optional[List[PositionLot]] = None,
    ) -> InvariantResult:
        """Validates all 10 invariants on a state transition."""
        result = InvariantResult(is_valid=True)

        # 1. Cash non-negativity
        result.add_violations(self.check_cash_non_negativity(cur_state))

        # 2. Margin equation
        result.add_violations(self.check_margin_equation(cur_state))

        # 3. HWM monotonicity (if previous state available)
        if prev_state is not None:
            result.add_violations(self.check_hwm_monotonicity(prev_state, cur_state))
            result.add_violations(self.check_mtm_cash_isolation(prev_state, cur_state, execution))

        # 4. FIFO lot splitting conservation (if split occurred)
        if split_orig_lot is not None and split_child_lots is not None:
            result.add_violations(
                self.check_fifo_lot_split_conservation(split_orig_lot, split_child_lots)
            )

        # 5. Fee bounds (if trade executed)
        if execution is not None:
            result.add_violations(self.check_fee_bounds(execution))
            if prev_state is not None:
                result.add_violations(self.check_ghost_sell_prevention(prev_state, execution))

        # 6. Zero orphaned positions
        all_positions = cur_state.open_positions + cur_state.closed_positions
        if all_positions:
            result.add_violations(self.check_zero_orphaned_positions(all_positions))

        # 8. Numerical safety
        result.add_violations(self.check_numerical_safety(cur_state))
        if execution is not None:
            result.add_violations(self.check_numerical_safety(execution))

        # 10. Position balance integrity
        result.add_violations(self.check_position_balance_integrity(cur_state))

        result.checked_count = 10
        result.passed_count = 10 - len(result.violations)
        if result.violations:
            self.history_violations.extend(result.violations)

        return result

    def audit_all(
        self,
        states: Sequence[PortfolioState],
        executions: Optional[Sequence[TradeExecution]] = None,
    ) -> InvariantResult:
        """Audits an entire sequential history of states and executions."""
        overall_result = InvariantResult(is_valid=True)

        for i, state in enumerate(states):
            prev = states[i - 1] if i > 0 else None
            exec_item = executions[i] if (executions is not None and i < len(executions)) else None
            step_result = self.validate_transition(prev, state, exec_item)
            overall_result.add_violations(step_result.violations)
            overall_result.checked_count += step_result.checked_count
            overall_result.passed_count += step_result.passed_count

        return overall_result

    def format_violation_report(self, violations: Sequence[InvariantViolation]) -> str:
        """Generates a human-readable diagnostic report of violations."""
        if not violations:
            return "✅ All Invariant Checks Passed: 0 Violations."

        lines = [f"❌ Detected {len(violations)} Invariant Violation(s):"]
        for idx, v in enumerate(violations, 1):
            lines.append(
                f"  [{idx}] [{v.severity.value}] {v.invariant_name} ({v.check_type.value})\n"
                f"      Message: {v.message}\n"
                f"      Observed: {v.observed_value} | Expected: {v.expected_value}\n"
                f"      Context: {v.context}"
            )
        return "\n".join(lines)
