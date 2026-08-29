"""
Baleen Unified Scenario Test Runner.

Executes deterministic stress scenarios across Tier 1 (Order Book Extremes),
Tier 2 (Timing & Settlement), Tier 3 (Lifecycle & FIFO), and Tier 4 (Multi-Tenancy).
Provides pre-, during-, and post-execution invariant auditing, metrics collection,
and comprehensive failure reporting.
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from tests.scenarios.invariant_monitor import (
    InvariantCheckType,
    InvariantMonitor,
    InvariantResult,
    InvariantViolation,
    PortfolioState,
    PositionLot,
    TradeExecution,
)
from tests.scenarios.mock_market_factory import (
    MockMarketFactory,
    OrderBookSnapshot,
    SyntheticEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class ScenarioDefinition:
    """Specification of a test scenario in the Baleen stress matrix."""
    scenario_id: str
    title: str
    tier: str  # e.g., "Tier 1: Order Book", "Tier 2: Timing/Network", "Tier 3: Lifecycle", "Tier 4: Multi-Tenancy"
    description: str
    initial_state: PortfolioState
    order_book_factory: Optional[Callable[[], OrderBookSnapshot]] = None
    events: List[SyntheticEvent] = field(default_factory=list)
    expected_invariants: List[InvariantCheckType] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class ScenarioStep:
    """Individual execution step in a scenario run."""
    step_number: int
    description: str
    event: Optional[SyntheticEvent]
    pre_state: PortfolioState
    post_state: PortfolioState
    execution: Optional[TradeExecution]
    violations: List[InvariantViolation] = field(default_factory=list)
    status: str = "PASS"  # PASS, FAIL, SKIPPED
    error: Optional[str] = None


@dataclass
class ScenarioResult:
    """Outcome of running a single scenario."""
    scenario_id: str
    title: str
    tier: str
    passed: bool
    steps: List[ScenarioStep] = field(default_factory=list)
    violations: List[InvariantViolation] = field(default_factory=list)
    execution_time_ms: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def violation_count(self) -> int:
        return len(self.violations)


@dataclass
class ScenarioReport:
    """Aggregated report across multiple scenario executions."""
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    total_violations: int = 0
    violations_by_type: Dict[str, int] = field(default_factory=dict)
    results: List[ScenarioResult] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def pass_rate_pct(self) -> float:
        if self.total_scenarios == 0:
            return 0.0
        return round((self.passed_scenarios / self.total_scenarios) * 100.0, 2)

    def summary(self) -> str:
        lines = [
            "=" * 70,
            "BALEEN SCENARIO STRESS MATRIX EXECUTION REPORT",
            "=" * 70,
            f"Total Scenarios Executed : {self.total_scenarios}",
            f"Passed                   : {self.passed_scenarios} ({self.pass_rate_pct}%)",
            f"Failed                   : {self.failed_scenarios}",
            f"Total Invariant Leaks    : {self.total_violations}",
            f"Execution Duration       : {self.total_time_ms:.2f} ms",
            "-" * 70,
        ]

        if self.violations_by_type:
            lines.append("Violations Breakdown by Invariant Type:")
            for v_type, count in self.violations_by_type.items():
                lines.append(f"  - {v_type}: {count}")
            lines.append("-" * 70)

        for res in self.results:
            status_icon = "[PASS]" if res.passed else "[FAIL]"
            lines.append(
                f"{status_icon} [{res.scenario_id}] {res.title} ({res.tier}) - {res.execution_time_ms:.2f}ms"
            )
            if not res.passed and res.violations:
                for v in res.violations:
                    lines.append(f"     [WARN] {v.invariant_name}: {v.message}")
            if res.error:
                lines.append(f"     [ERROR] Exception: {res.error}")

        lines.append("=" * 70)
        return "\n".join(lines)


# Type alias for custom step execution handler
StepHandler = Callable[
    [PortfolioState, SyntheticEvent, Optional[OrderBookSnapshot]],
    Tuple[PortfolioState, Optional[TradeExecution], Optional[PositionLot], Optional[List[PositionLot]]],
]


class ScenarioRunner:
    """Parametric runner executing scenario definitions against invariant monitors."""

    def __init__(self, strict_invariants: bool = True):
        self.strict_invariants = strict_invariants
        self.monitor = InvariantMonitor(strict_mode=strict_invariants)

    def default_step_executor(
        self,
        current_state: PortfolioState,
        event: SyntheticEvent,
        order_book: Optional[OrderBookSnapshot] = None,
    ) -> Tuple[PortfolioState, Optional[TradeExecution], Optional[PositionLot], Optional[List[PositionLot]]]:
        """
        Default state machine transition logic for simulating order fills,
        FIFO lot splitting, fee calculation, and cash/margin updates.
        """
        new_state = copy.deepcopy(current_state)
        new_state.timestamp = event.arrival_timestamp

        # Categorize fee
        from app.services.polymarket_fees import calculate_polymarket_fee

        trade_price = max(0.001, min(0.999, event.price))
        fee_info = calculate_polymarket_fee(
            notional_usd=event.notional_usd,
            price=trade_price,
            market_title=event.market_question,
            is_maker=False,
        )
        fee_usd = float(fee_info["fee_usd"])
        split_orig: Optional[PositionLot] = None
        split_children: Optional[List[PositionLot]] = None

        if event.side.upper() == "BUY":
            # Check cash ceiling
            if new_state.free_cash_usd < event.notional_usd:
                # Sizing limited to free cash
                effective_notional = max(0.0, new_state.free_cash_usd)
            else:
                effective_notional = event.notional_usd

            if effective_notional <= 0.0:
                # Trade skipped due to 0 free cash
                exec_log = TradeExecution(
                    trade_id=f"tx_{event.event_id}",
                    condition_id=event.condition_id,
                    outcome=event.outcome,
                    side="BUY",
                    price=trade_price,
                    shares=0.0,
                    notional_usd=0.0,
                    fee_usd=0.0,
                    user_id=new_state.user_id,
                    wallet_address=event.wallet_address,
                    market_title=event.market_question,
                    market_category=event.market_category,
                    status="SKIPPED",
                    failure_detail="INSUFFICIENT_FREE_CASH",
                )
                return new_state, exec_log, None, None

            # Recompute fee on actual effective notional
            fee_info = calculate_polymarket_fee(
                notional_usd=effective_notional,
                price=trade_price,
                market_title=event.market_question,
                is_maker=False,
            )
            fee_usd = float(fee_info["fee_usd"])

            shares_filled = effective_notional / trade_price
            new_lot = PositionLot(
                lot_id=f"lot_{event.event_id}",
                condition_id=event.condition_id,
                outcome=event.outcome,
                side="BUY",
                price=trade_price,
                shares=shares_filled,
                notional_usd=effective_notional,
                fee_usd=fee_usd,
                status="FILLED",
                user_id=new_state.user_id,
                wallet_address=event.wallet_address,
                market_question=event.market_question,
                market_category=event.market_category,
                created_at=event.arrival_timestamp,
            )
            new_state.open_positions.append(new_lot)

            # Update margin & free cash
            new_state.open_margin_usd = round(new_state.total_open_notional(), 2)
            new_state.free_cash_usd = round(
                max(0.0, new_state.settled_cash_usd - new_state.open_margin_usd), 2
            )
            new_state.equity_usd = round(
                new_state.settled_cash_usd + new_state.total_unrealized_pnl_usd, 2
            )

            exec_log = TradeExecution(
                trade_id=f"tx_{event.event_id}",
                condition_id=event.condition_id,
                outcome=event.outcome,
                side="BUY",
                price=trade_price,
                shares=shares_filled,
                notional_usd=effective_notional,
                fee_usd=fee_usd,
                user_id=new_state.user_id,
                wallet_address=event.wallet_address,
                market_title=event.market_question,
                market_category=event.market_category,
                status="FILLED",
            )
            return new_state, exec_log, None, None

        elif event.side.upper() == "SELL":
            # Find open BUY lots for this condition and outcome
            open_buys = [
                lot
                for lot in new_state.open_positions
                if lot.condition_id == event.condition_id
                and lot.outcome.lower() == event.outcome.lower()
                and lot.status == "FILLED"
                and lot.side == "BUY"
            ]

            if not open_buys:
                # Ghost sell guard: User has 0 open positions
                exec_log = TradeExecution(
                    trade_id=f"tx_{event.event_id}",
                    condition_id=event.condition_id,
                    outcome=event.outcome,
                    side="SELL",
                    price=trade_price,
                    shares=0.0,
                    notional_usd=0.0,
                    fee_usd=0.0,
                    user_id=new_state.user_id,
                    wallet_address=event.wallet_address,
                    market_title=event.market_question,
                    status="SKIPPED",
                    failure_detail="ZERO_HELD_POSITIONS",
                )
                return new_state, exec_log, None, None

            remaining_sell_notional = event.notional_usd
            total_sell_shares = 0.0
            realized_pnl_sum = 0.0

            for buy_lot in list(open_buys):
                if remaining_sell_notional <= 0:
                    break

                price_ratio = (trade_price - buy_lot.price) / buy_lot.price if buy_lot.price > 0 else 0.0

                if buy_lot.notional_usd <= remaining_sell_notional + 0.01:
                    # Full close of this lot
                    buy_lot.status = "CLOSED"
                    buy_lot.closed_at = event.arrival_timestamp
                    lot_pnl = round(buy_lot.notional_usd * price_ratio - (buy_lot.fee_usd + fee_usd * (buy_lot.notional_usd / event.notional_usd)), 2)
                    buy_lot.realized_pnl_usd = lot_pnl
                    realized_pnl_sum += lot_pnl
                    total_sell_shares += buy_lot.shares
                    remaining_sell_notional -= buy_lot.notional_usd

                    new_state.open_positions.remove(buy_lot)
                    new_state.closed_positions.append(buy_lot)
                else:
                    # Partial FIFO split
                    closed_notional = remaining_sell_notional
                    remaining_notional = round(buy_lot.notional_usd - closed_notional, 2)
                    closed_shares = round(closed_notional / buy_lot.price, 4)
                    remaining_shares = round(buy_lot.shares - closed_shares, 4)

                    fee_rate = buy_lot.fee_usd / buy_lot.notional_usd if buy_lot.notional_usd > 0 else 0.0
                    closed_fee = round(closed_notional * fee_rate, 4)
                    remaining_fee = round(buy_lot.fee_usd - closed_fee, 4)

                    split_orig = copy.deepcopy(buy_lot)

                    # Update existing lot to closed portion
                    buy_lot.status = "CLOSED"
                    buy_lot.notional_usd = closed_notional
                    buy_lot.shares = closed_shares
                    buy_lot.fee_usd = closed_fee
                    buy_lot.closed_at = event.arrival_timestamp
                    lot_pnl = round(closed_notional * price_ratio - (closed_fee + fee_usd * (closed_notional / event.notional_usd)), 2)
                    buy_lot.realized_pnl_usd = lot_pnl
                    realized_pnl_sum += lot_pnl
                    total_sell_shares += closed_shares

                    new_state.open_positions.remove(buy_lot)
                    new_state.closed_positions.append(buy_lot)

                    # Create remaining split lot
                    child_lot = PositionLot(
                        lot_id=f"{buy_lot.lot_id}_split",
                        condition_id=buy_lot.condition_id,
                        outcome=buy_lot.outcome,
                        side="BUY",
                        price=buy_lot.price,
                        shares=remaining_shares,
                        notional_usd=remaining_notional,
                        fee_usd=remaining_fee,
                        status="FILLED",
                        user_id=new_state.user_id,
                        wallet_address=buy_lot.wallet_address,
                        market_question=buy_lot.market_question,
                        market_category=buy_lot.market_category,
                        parent_lot_id=buy_lot.lot_id,
                        created_at=buy_lot.created_at,
                    )
                    new_state.open_positions.append(child_lot)

                    split_children = [buy_lot, child_lot]
                    remaining_sell_notional = 0.0
                    break

            # Update settled cash and HWM
            new_state.total_realized_pnl_usd = round(
                new_state.total_realized_pnl_usd + realized_pnl_sum, 2
            )
            new_state.settled_cash_usd = round(new_state.settled_cash_usd + realized_pnl_sum, 2)
            new_state.open_margin_usd = round(new_state.total_open_notional(), 2)
            new_state.free_cash_usd = round(
                max(0.0, new_state.settled_cash_usd - new_state.open_margin_usd), 2
            )
            new_state.equity_usd = round(
                new_state.settled_cash_usd + new_state.total_unrealized_pnl_usd, 2
            )

            # High-water mark ratchets only when total equity exceeds previous HWM
            if new_state.equity_usd > new_state.high_water_mark_usd:
                new_state.high_water_mark_usd = new_state.equity_usd

            exec_log = TradeExecution(
                trade_id=f"tx_{event.event_id}",
                condition_id=event.condition_id,
                outcome=event.outcome,
                side="SELL",
                price=trade_price,
                shares=total_sell_shares,
                notional_usd=event.notional_usd - remaining_sell_notional,
                fee_usd=fee_usd,
                user_id=new_state.user_id,
                wallet_address=event.wallet_address,
                market_title=event.market_question,
                market_category=event.market_category,
                status="FILLED",
            )
            return new_state, exec_log, split_orig, split_children

        return new_state, None, None, None

    def run_scenario(
        self,
        scenario: ScenarioDefinition,
        step_executor: Optional[StepHandler] = None,
    ) -> ScenarioResult:
        """Executes a single test scenario and validates all invariants."""
        start_time = time.perf_counter()
        executor = step_executor or self.default_step_executor

        steps: List[ScenarioStep] = []
        all_violations: List[InvariantViolation] = []
        cur_state = copy.deepcopy(scenario.initial_state)

        # 1. Pre-execution initial state validation
        initial_check = self.monitor.validate_transition(None, cur_state)
        if not initial_check.is_valid:
            all_violations.extend(initial_check.violations)

        order_book = scenario.order_book_factory() if scenario.order_book_factory else None

        # 2. Step-by-step event execution
        for step_idx, event in enumerate(scenario.events, 1):
            pre_state = copy.deepcopy(cur_state)
            step_error: Optional[str] = None
            step_violations: List[InvariantViolation] = []
            exec_log: Optional[TradeExecution] = None
            split_orig: Optional[PositionLot] = None
            split_children: Optional[List[PositionLot]] = None

            try:
                cur_state, exec_log, split_orig, split_children = executor(
                    pre_state, event, order_book
                )
            except Exception as e:
                logger.error(f"Scenario {scenario.scenario_id} step {step_idx} error: {e}", exc_info=True)
                step_error = str(e)

            # Invariant check for this transition
            transition_check = self.monitor.validate_transition(
                prev_state=pre_state,
                cur_state=cur_state,
                execution=exec_log,
                split_orig_lot=split_orig,
                split_child_lots=split_children,
            )

            if not transition_check.is_valid:
                step_violations.extend(transition_check.violations)
                all_violations.extend(transition_check.violations)

            status = "FAIL" if (step_error or step_violations) else "PASS"
            steps.append(
                ScenarioStep(
                    step_number=step_idx,
                    description=f"{event.side} ${event.notional_usd:.2f} on {event.condition_id}",
                    event=event,
                    pre_state=pre_state,
                    post_state=cur_state,
                    execution=exec_log,
                    violations=step_violations,
                    status=status,
                    error=step_error,
                )
            )

        # 3. Post-execution comprehensive audit
        all_positions = cur_state.open_positions + cur_state.closed_positions
        if all_positions:
            orphaned_violations = self.monitor.check_zero_orphaned_positions(all_positions)
            if orphaned_violations:
                all_violations.extend(orphaned_violations)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        passed = len(all_violations) == 0 and all(s.status == "PASS" for s in steps)

        metrics = {
            "final_settled_cash": cur_state.settled_cash_usd,
            "final_free_cash": cur_state.free_cash_usd,
            "final_open_margin": cur_state.open_margin_usd,
            "final_hwm": cur_state.high_water_mark_usd,
            "final_equity": cur_state.equity_usd,
            "total_open_positions": len(cur_state.open_positions),
            "total_closed_positions": len(cur_state.closed_positions),
            "realized_pnl": cur_state.total_realized_pnl_usd,
        }

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            title=scenario.title,
            tier=scenario.tier,
            passed=passed,
            steps=steps,
            violations=all_violations,
            execution_time_ms=round(elapsed_ms, 2),
            metrics=metrics,
        )

    def run_matrix(
        self,
        scenarios: Sequence[ScenarioDefinition],
        step_executor: Optional[StepHandler] = None,
    ) -> ScenarioReport:
        """Runs a matrix of scenario definitions and aggregates findings."""
        start_time = time.perf_counter()
        results: List[ScenarioResult] = []
        violations_by_type: Dict[str, int] = {}
        total_violations = 0
        passed_count = 0
        failed_count = 0

        for scenario in scenarios:
            res = self.run_scenario(scenario, step_executor=step_executor)
            results.append(res)

            if res.passed:
                passed_count += 1
            else:
                failed_count += 1

            for v in res.violations:
                total_violations += 1
                violations_by_type[v.check_type.value] = (
                    violations_by_type.get(v.check_type.value, 0) + 1
                )

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return ScenarioReport(
            total_scenarios=len(scenarios),
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            total_violations=total_violations,
            violations_by_type=violations_by_type,
            results=results,
            total_time_ms=round(total_elapsed_ms, 2),
        )
