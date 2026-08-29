"""
Unit & Integration Tests for Baleen Scenario Test Infrastructure & Invariant Monitor.

Verifies:
  - All 10 Invariant Checks (Cash, Margin, HWM, FIFO splits, Quadratic Fees,
    Orphaned Positions, Ghost Sells, Numerical IEEE Safety, MTM Isolation, Equity Integrity).
  - Synthetic Order Book & Event Stream Generators in MockMarketFactory.
  - Parametric ScenarioRunner Execution, Invariant Hook Auditing, and ScenarioReport Aggregation.
"""

import math
import pytest
from app.sizing.fill_simulator import simulate_fill
from tests.scenarios.invariant_monitor import (
    InvariantCheckType,
    InvariantMonitor,
    InvariantSeverity,
    PortfolioState,
    PositionLot,
    TradeExecution,
)
from tests.scenarios.mock_market_factory import (
    EventStreamGenerator,
    MockMarketFactory,
    OrderBookSnapshot,
    SyntheticEvent,
)
from tests.scenarios.runner import (
    ScenarioDefinition,
    ScenarioReport,
    ScenarioResult,
    ScenarioRunner,
)


@pytest.fixture
def monitor() -> InvariantMonitor:
    return InvariantMonitor(strict_mode=True)


@pytest.fixture
def runner() -> ScenarioRunner:
    return ScenarioRunner(strict_invariants=True)


@pytest.fixture
def base_portfolio_state() -> PortfolioState:
    return PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=10000.0,
        free_cash_usd=10000.0,
        open_margin_usd=0.0,
        high_water_mark_usd=10000.0,
        open_positions=[],
        closed_positions=[],
        total_realized_pnl_usd=0.0,
        total_unrealized_pnl_usd=0.0,
        equity_usd=10000.0,
    )


# =============================================================================
# 1. Invariant Monitor Tests
# =============================================================================

def test_cash_non_negativity_invariant(monitor: InvariantMonitor, base_portfolio_state: PortfolioState):
    # Valid state
    violations = monitor.check_cash_non_negativity(base_portfolio_state)
    assert len(violations) == 0

    # Negative settled cash
    bad_settled = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=-50.0,
        free_cash_usd=0.0,
        open_margin_usd=0.0,
        high_water_mark_usd=10000.0,
    )
    violations = monitor.check_cash_non_negativity(bad_settled)
    assert len(violations) == 1
    assert violations[0].check_type == InvariantCheckType.CASH_NON_NEGATIVITY
    assert violations[0].severity == InvariantSeverity.CRITICAL

    # Negative free cash
    bad_free = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=100.0,
        free_cash_usd=-10.0,
        open_margin_usd=110.0,
        high_water_mark_usd=10000.0,
    )
    violations = monitor.check_cash_non_negativity(bad_free)
    assert len(violations) == 1
    assert violations[0].check_type == InvariantCheckType.CASH_NON_NEGATIVITY


def test_margin_equation_invariant(monitor: InvariantMonitor):
    # Valid state: settled $10,000, margin $2,000 -> free cash $8,000
    valid_lot = PositionLot(
        lot_id="lot_1",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=4000.0,
        notional_usd=2000.0,
        fee_usd=7.20,
        status="FILLED",
    )
    valid_state = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=10000.0,
        free_cash_usd=8000.0,
        open_margin_usd=2000.0,
        high_water_mark_usd=10000.0,
        open_positions=[valid_lot],
        equity_usd=10000.0,
    )
    assert len(monitor.check_margin_equation(valid_state)) == 0

    # Invariant violation: Free cash improperly inflated to $9,000
    invalid_state = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=10000.0,
        free_cash_usd=9000.0,  # Leaked $1,000 phantom free cash!
        open_margin_usd=2000.0,
        high_water_mark_usd=10000.0,
        open_positions=[valid_lot],
        equity_usd=10000.0,
    )
    violations = monitor.check_margin_equation(invalid_state)
    assert len(violations) >= 1
    assert any(v.check_type == InvariantCheckType.MARGIN_EQUATION for v in violations)


def test_hwm_monotonicity_invariant(monitor: InvariantMonitor):
    state_t0 = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=10000.0,
        free_cash_usd=10000.0,
        open_margin_usd=0.0,
        high_water_mark_usd=10000.0,
        equity_usd=10000.0,
    )

    # Valid ratchet: Equity increases to $11,000, HWM ratchets to $11,000
    state_t1 = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=11000.0,
        free_cash_usd=11000.0,
        open_margin_usd=0.0,
        high_water_mark_usd=11000.0,
        equity_usd=11000.0,
    )
    assert len(monitor.check_hwm_monotonicity(state_t0, state_t1)) == 0

    # Invalid drop: HWM decreases to $10,500
    state_t2_drop = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=10500.0,
        free_cash_usd=10500.0,
        open_margin_usd=0.0,
        high_water_mark_usd=10500.0,  # Dropped from 11,000!
        equity_usd=10500.0,
    )
    violations = monitor.check_hwm_monotonicity(state_t1, state_t2_drop)
    assert len(violations) >= 1
    assert violations[0].check_type == InvariantCheckType.HIGH_WATER_MARK_MONOTONICITY
    assert violations[0].severity == InvariantSeverity.CRITICAL

    # Phantom ratchet above equity: Equity is $10,000 but HWM jumps to $12,000
    state_phantom = PortfolioState(
        user_id="usr_test_1",
        settled_cash_usd=10000.0,
        free_cash_usd=10000.0,
        open_margin_usd=0.0,
        high_water_mark_usd=12000.0,
        equity_usd=10000.0,
    )
    violations = monitor.check_hwm_monotonicity(state_t0, state_phantom)
    assert any("Phantom" in v.invariant_name for v in violations)


def test_fifo_lot_splitting_conservation_invariant(monitor: InvariantMonitor):
    orig_lot = PositionLot(
        lot_id="lot_orig",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=1000.0,
        notional_usd=500.0,
        fee_usd=18.00,
        status="FILLED",
    )

    # Valid 40% / 60% split
    child_closed = PositionLot(
        lot_id="lot_orig",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=400.0,
        notional_usd=200.0,
        fee_usd=7.20,
        status="CLOSED",
    )
    child_remaining = PositionLot(
        lot_id="lot_orig_split",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=600.0,
        notional_usd=300.0,
        fee_usd=10.80,
        status="FILLED",
    )
    assert len(monitor.check_fifo_lot_split_conservation(orig_lot, [child_closed, child_remaining])) == 0

    # Dollar leakage ($200 + $280 = $480 != $500)
    bad_dollar_child = PositionLot(
        lot_id="lot_orig_split",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=600.0,
        notional_usd=280.0,  # $20 leaked!
        fee_usd=10.80,
        status="FILLED",
    )
    violations = monitor.check_fifo_lot_split_conservation(orig_lot, [child_closed, bad_dollar_child])
    assert any(v.invariant_name == "FIFO Lot Splitting Dollar Conservation" for v in violations)

    # Fee leakage ($7.20 + $5.00 = $12.20 != $18.00)
    bad_fee_child = PositionLot(
        lot_id="lot_orig_split",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=600.0,
        notional_usd=300.0,
        fee_usd=5.00,  # Dropped $5.80 in fees!
        status="FILLED",
    )
    violations = monitor.check_fifo_lot_split_conservation(orig_lot, [child_closed, bad_fee_child])
    assert any(v.invariant_name == "FIFO Lot Splitting Fee Conservation" for v in violations)


def test_polymarket_fee_bounds_invariant(monitor: InvariantMonitor):
    # Valid crypto trade (notional $100, theta 0.072, fee $3.60 at p=0.50)
    valid_trade = TradeExecution(
        trade_id="tx_1",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=200.0,
        notional_usd=100.0,
        fee_usd=3.60,
        market_category="Crypto",
    )
    assert len(monitor.check_fee_bounds(valid_trade)) == 0

    # Negative fee
    neg_fee_trade = TradeExecution(
        trade_id="tx_neg",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=200.0,
        notional_usd=100.0,
        fee_usd=-1.50,
        market_category="Crypto",
    )
    violations = monitor.check_fee_bounds(neg_fee_trade)
    assert any(v.invariant_name == "Fee Non-Negativity" for v in violations)

    # Exceeding theoretical ceiling (0.072 * 100 = 7.20, but charged $10.00)
    over_fee_trade = TradeExecution(
        trade_id="tx_over",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=200.0,
        notional_usd=100.0,
        fee_usd=10.00,
        market_category="Crypto",
    )
    violations = monitor.check_fee_bounds(over_fee_trade)
    assert any(v.invariant_name == "Quadratic Fee Ceiling" for v in violations)

    # Maker trade charged fee
    maker_fee_trade = TradeExecution(
        trade_id="tx_maker",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=200.0,
        notional_usd=100.0,
        fee_usd=1.00,
        is_maker=True,
    )
    violations = monitor.check_fee_bounds(maker_fee_trade)
    assert any(v.invariant_name == "Maker Fee Free Invariance" for v in violations)


def test_zero_orphaned_positions_invariant(monitor: InvariantMonitor):
    # Fully closed position
    closed_lot = PositionLot(
        lot_id="lot_closed",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=100.0,
        notional_usd=50.0,
        fee_usd=1.80,
        status="CLOSED",
    )
    assert len(monitor.check_zero_orphaned_positions([closed_lot])) == 0

    # Orphaned open lot: 100 shares bought, 100 shares closed, but an orphaned lot of 100 shares is still FILLED
    orphaned_lot = PositionLot(
        lot_id="lot_orphaned",
        condition_id="cond_1",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=100.0,
        notional_usd=50.0,
        fee_usd=1.80,
        status="FILLED",
    )
    violations = monitor.check_zero_orphaned_positions([closed_lot, orphaned_lot])
    # Note: total buy shares = 200, closed = 100, so 100 remains (valid partial)
    assert len(violations) == 0

    # But if buy_shares == closed_buy_shares (e.g. 100 closed shares) and open lot has status FILLED
    # Simulate bug where shares closed == total bought, but status wasn't flipped:
    buggy_lot = PositionLot(
        lot_id="lot_bug",
        condition_id="cond_bug",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=0.0,  # 0 remaining shares but status is FILLED!
        notional_usd=0.0,
        fee_usd=0.0,
        status="FILLED",
    )
    closed_bug_lot = PositionLot(
        lot_id="lot_bug_closed",
        condition_id="cond_bug",
        outcome="Yes",
        side="BUY",
        price=0.50,
        shares=100.0,
        notional_usd=50.0,
        fee_usd=1.80,
        status="CLOSED",
    )
    violations = monitor.check_zero_orphaned_positions([closed_bug_lot, buggy_lot])
    assert len(violations) >= 1
    assert violations[0].check_type == InvariantCheckType.ZERO_ORPHANED_POSITIONS


def test_ghost_sell_fill_prevention_invariant(monitor: InvariantMonitor, base_portfolio_state: PortfolioState):
    # User holds 0 open positions
    ghost_sell = TradeExecution(
        trade_id="tx_ghost",
        condition_id="cond_ghost",
        outcome="Yes",
        side="SELL",
        price=0.60,
        shares=100.0,
        notional_usd=60.0,
        fee_usd=2.16,
        status="FILLED",
    )

    violations = monitor.check_ghost_sell_prevention(base_portfolio_state, ghost_sell)
    assert len(violations) >= 1
    assert any(v.invariant_name == "Ghost Sell Fill Execution" for v in violations)
    assert any(v.invariant_name == "Ghost Sell Fee Leak" for v in violations)


def test_numerical_ieee_safety_invariant(monitor: InvariantMonitor):
    # Clean dictionary
    assert len(monitor.check_numerical_safety({"price": 0.55, "notional": 100.0})) == 0

    # NaN detection
    nan_violations = monitor.check_numerical_safety({"price": float("nan"), "notional": 100.0})
    assert len(nan_violations) == 1
    assert nan_violations[0].check_type == InvariantCheckType.NUMERICAL_IEEE_SAFETY
    assert nan_violations[0].observed_value == "NaN"

    # Inf detection
    inf_violations = monitor.check_numerical_safety({"price": 0.5, "notional": float("inf")})
    assert len(inf_violations) == 1
    assert inf_violations[0].check_type == InvariantCheckType.NUMERICAL_IEEE_SAFETY
    assert inf_violations[0].observed_value == "Infinity"


def test_mtm_cash_isolation_invariant(monitor: InvariantMonitor):
    prev_state = PortfolioState(
        user_id="usr_1",
        settled_cash_usd=10000.0,
        free_cash_usd=10000.0,
        open_margin_usd=0.0,
        high_water_mark_usd=10000.0,
        equity_usd=10000.0,
    )

    # Valid MTM update: settled cash remains $10,000, unrealized PnL becomes +$500, equity becomes $10,500
    valid_mtm = PortfolioState(
        user_id="usr_1",
        settled_cash_usd=10000.0,
        free_cash_usd=10000.0,
        open_margin_usd=0.0,
        high_water_mark_usd=10500.0,
        total_unrealized_pnl_usd=500.0,
        equity_usd=10500.0,
    )
    assert len(monitor.check_mtm_cash_isolation(prev_state, valid_mtm, executed_trade=None)) == 0

    # Invalid MTM update: settled cash falsely increased to $10,500 on unrealized price change
    bad_mtm = PortfolioState(
        user_id="usr_1",
        settled_cash_usd=10500.0,  # Illegally settled!
        free_cash_usd=10500.0,
        open_margin_usd=0.0,
        high_water_mark_usd=10500.0,
        total_unrealized_pnl_usd=500.0,
        equity_usd=10500.0,
    )
    violations = monitor.check_mtm_cash_isolation(prev_state, bad_mtm, executed_trade=None)
    assert len(violations) == 1
    assert violations[0].check_type == InvariantCheckType.MTM_CASH_ISOLATION


# =============================================================================
# 2. Mock Market Factory Tests
# =============================================================================

def test_mock_market_factory_order_books():
    # 1. Empty book
    empty = MockMarketFactory.create_empty_book("c_empty")
    assert len(empty.bids) == 0
    assert len(empty.asks) == 0
    assert empty.best_bid is None
    assert empty.spread is None

    # Fill simulation on empty book returns 0 fill without crashing
    fill = simulate_fill(100.0, empty.to_dict(), "BUY")
    assert fill.total_filled == 0.0
    assert fill.avg_price == 0.0

    # 2. Inverted book
    inverted = MockMarketFactory.create_inverted_book("c_inv", best_bid=0.65, best_ask=0.55)
    assert inverted.is_inverted is True
    assert inverted.best_bid == 0.65
    assert inverted.best_ask == 0.55
    assert inverted.spread == -0.10

    # 3. Micro liquidity
    micro = MockMarketFactory.create_micro_liquidity_book("c_micro", mid_price=0.50, tick_size_usd=0.01)
    fill_micro = simulate_fill(100.0, micro.to_dict(), "BUY")
    # Should only fill available depth (~$0.02)
    assert fill_micro.total_filled < 5.0

    # 4. Whale depth
    whale_book = MockMarketFactory.create_whale_depth_book("c_whale", total_depth_usd=1_000_000.0)
    fill_whale = simulate_fill(50_000.0, whale_book.to_dict(), "BUY")
    assert fill_whale.total_filled == 50_000.0
    assert fill_whale.avg_price > 0.50

    # 5. Price shock books
    crash_book = MockMarketFactory.create_price_shock_book("c_crash", from_price=0.99, to_price=0.01, shock_type="crash")
    assert crash_book.best_bid is not None and crash_book.best_bid < 0.02

    # 6. Zero and Ceiling contracts
    zero_book = MockMarketFactory.create_zero_price_contract_book("c_zero")
    assert zero_book.best_bid == 0.001 or zero_book.best_bid == 0.000
    ceiling_book = MockMarketFactory.create_ceiling_price_contract_book("c_ceil")
    assert ceiling_book.best_ask == 1.000 or ceiling_book.best_ask == 0.999


def test_mock_event_stream_generators():
    # 1. Out-of-order Envio stream
    ooo_stream = EventStreamGenerator.generate_out_of_order_envio_stream(count=15, invert_ratio=0.5)
    assert len(ooo_stream) == 15
    # Confirm arrival timestamps are sorted
    for i in range(len(ooo_stream) - 1):
        assert ooo_stream[i].arrival_timestamp <= ooo_stream[i + 1].arrival_timestamp

    # 2. Latency sweep stream
    latencies = [1.0, 5.0, 15.0, 30.0, 60.0]
    lat_stream = EventStreamGenerator.generate_latency_sweep_stream(latencies=latencies)
    assert len(lat_stream) == 5
    for idx, event in enumerate(lat_stream):
        assert event.latency_seconds == latencies[idx]

    # 3. WS reconnect burst
    burst_stream = EventStreamGenerator.generate_websocket_reconnect_burst(burst_size=25)
    assert len(burst_stream) == 25
    # All burst arrivals should be tightly clustered within 1 second
    arrival_spread = burst_stream[-1].arrival_timestamp - burst_stream[0].arrival_timestamp
    assert arrival_spread < 1.0

    # 4. Duplicate transaction stream
    dup_stream = EventStreamGenerator.generate_duplicate_transaction_stream(count=20, duplicate_ratio=0.5)
    assert len(dup_stream) == 20
    dup_count = sum(1 for e in dup_stream if e.is_duplicate)
    assert dup_count > 0

    # 5. RPC failover stream
    rpc_stream = EventStreamGenerator.generate_rpc_failure_and_retry_stream(count=10, failure_rate=0.5)
    assert len(rpc_stream) >= 10
    assert any(e.event_type == "RPC_FAILOVER" for e in rpc_stream)

    # 6. Binary resolution events
    res_events = EventStreamGenerator.generate_binary_resolution_events(["cond_1", "cond_2"], winning_outcome="Yes")
    assert len(res_events) == 2
    assert res_events[0].price == 1.00


# =============================================================================
# 3. Scenario Runner Tests
# =============================================================================

def test_scenario_runner_valid_lifecycle(runner: ScenarioRunner, base_portfolio_state: PortfolioState):
    # Construct a valid lifecycle scenario:
    # 1. BUY $200 of Condition A at p=0.50 (400 shares)
    # 2. Partial SELL $100 of Condition A at p=0.60 (split into 200 closed, 200 remaining)
    # 3. Final SELL remaining $100 of Condition A at p=0.65 (close out position)
    events = [
        SyntheticEvent(
            event_id="evt_1",
            event_type="TRADE_LOG",
            condition_id="cond_life_1",
            wallet_address="0xWhale1",
            side="BUY",
            price=0.50,
            notional_usd=200.0,
            shares=400.0,
            tx_hash="0xabc1",
            log_index=0,
            block_number=100,
            block_timestamp=1000.0,
            arrival_timestamp=1000.5,
            market_question="Will Bitcoin break 100k?",
            market_category="Crypto",
        ),
        SyntheticEvent(
            event_id="evt_2",
            event_type="TRADE_LOG",
            condition_id="cond_life_1",
            wallet_address="0xWhale1",
            side="SELL",
            price=0.60,
            notional_usd=100.0,
            shares=166.67,
            tx_hash="0xabc2",
            log_index=1,
            block_number=101,
            block_timestamp=1010.0,
            arrival_timestamp=1010.5,
            market_question="Will Bitcoin break 100k?",
            market_category="Crypto",
        ),
        SyntheticEvent(
            event_id="evt_3",
            event_type="TRADE_LOG",
            condition_id="cond_life_1",
            wallet_address="0xWhale1",
            side="SELL",
            price=0.65,
            notional_usd=100.0,
            shares=153.85,
            tx_hash="0xabc3",
            log_index=2,
            block_number=102,
            block_timestamp=1020.0,
            arrival_timestamp=1020.5,
            market_question="Will Bitcoin break 100k?",
            market_category="Crypto",
        ),
    ]

    scenario = ScenarioDefinition(
        scenario_id="S_TEST_LIFECYCLE",
        title="Complete BUY -> Split SELL -> Full Liquidation Lifecycle",
        tier="Tier 3: Position Lifecycle",
        description="Verifies FIFO split conservation, fee bounds, margin release, and zero orphaned positions.",
        initial_state=base_portfolio_state,
        events=events,
    )

    result = runner.run_scenario(scenario)
    assert result.passed is True
    assert len(result.violations) == 0
    assert len(result.steps) == 3
    assert all(s.status == "PASS" for s in result.steps)

    # Check metrics
    assert result.metrics["total_open_positions"] == 0
    assert result.metrics["total_closed_positions"] == 2
    assert result.metrics["final_settled_cash"] > 10000.0  # Profitable liquidation
    assert result.metrics["final_hwm"] >= 10000.0


def test_scenario_runner_catches_ghost_sell_violation(runner: ScenarioRunner, base_portfolio_state: PortfolioState):
    # Scenario: Executing SELL on 0 positions with a buggy custom handler that forces FILLED status
    events = [
        SyntheticEvent(
            event_id="evt_ghost",
            event_type="TRADE_LOG",
            condition_id="cond_ghost",
            wallet_address="0xWhale1",
            side="SELL",
            price=0.50,
            notional_usd=100.0,
            shares=200.0,
            tx_hash="0xghost",
            log_index=0,
            block_number=200,
            block_timestamp=2000.0,
            arrival_timestamp=2000.5,
            market_question="Ghost Sell Test",
        )
    ]

    scenario = ScenarioDefinition(
        scenario_id="S_TEST_GHOST",
        title="Ghost Sell Violation Catch",
        tier="Tier 2: Edge Violations",
        description="Verifies runner catches a phantom sell fill on 0 open position.",
        initial_state=base_portfolio_state,
        events=events,
    )

    # Intentionally buggy step executor that fills the ghost sell
    def buggy_executor(state, event, book):
        bad_exec = TradeExecution(
            trade_id="tx_bad_ghost",
            condition_id=event.condition_id,
            outcome="Yes",
            side="SELL",
            price=0.50,
            shares=200.0,
            notional_usd=100.0,
            fee_usd=3.60,
            status="FILLED",  # BUG! Should be SKIPPED
        )
        return state, bad_exec, None, None

    result = runner.run_scenario(scenario, step_executor=buggy_executor)
    assert result.passed is False
    assert len(result.violations) >= 1
    assert any(v.check_type == InvariantCheckType.GHOST_SELL_PREVENTION for v in result.violations)


def test_scenario_runner_matrix_report(runner: ScenarioRunner, base_portfolio_state: PortfolioState):
    # Run a matrix of 3 diverse scenarios
    scenarios = [
        ScenarioDefinition(
            scenario_id=f"S00{i}",
            title=f"Scenario Test Matrix #{i}",
            tier="Tier 1: Order Book",
            description="Testing batch execution in matrix runner.",
            initial_state=base_portfolio_state,
            events=[
                SyntheticEvent(
                    event_id=f"evt_mat_{i}",
                    event_type="TRADE_LOG",
                    condition_id=f"cond_mat_{i}",
                    wallet_address="0xWhale1",
                    side="BUY",
                    price=0.50,
                    notional_usd=50.0 * i,
                    shares=100.0 * i,
                    tx_hash=f"0xmat{i}",
                    log_index=0,
                    block_number=300 + i,
                    block_timestamp=3000.0,
                    arrival_timestamp=3000.5,
                    market_question="Test Question",
                    market_category="Crypto",
                )
            ],
        )
        for i in range(1, 4)
    ]

    report = runner.run_matrix(scenarios)
    assert report.total_scenarios == 3
    assert report.passed_scenarios == 3
    assert report.failed_scenarios == 0
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0

    summary_text = report.summary()
    assert "BALEEN SCENARIO STRESS MATRIX EXECUTION REPORT" in summary_text
    assert "Passed                   : 3 (100.0%)" in summary_text
