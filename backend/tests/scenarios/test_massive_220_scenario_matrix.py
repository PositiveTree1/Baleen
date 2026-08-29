"""
Baleen Massive 220-Scenario Stress Matrix & State Machine Invariant Test Suite.

Executes 220 distinct operational, market, execution, network, and numerical
scenarios across 4 comprehensive tiers:
  - Tier 1: Order Book & Liquidity Extremes (55 scenarios)
  - Tier 2: Timing, Network & Settlement Dynamics (55 scenarios)
  - Tier 3: Complex Position & Lifecycle Sequences (55 scenarios)
  - Tier 4: Multi-Tenancy & Portfolio Scaling (55 scenarios)

Validates all 10 core system invariants:
  1. Cash Non-Negativity
  2. Settled Cash - Open Margin Conservation
  3. High-Water Mark Monotonicity
  4. FIFO Lot Splitting & Conservation
  5. Polymarket Quadratic Fee Bounds
  6. Zero Orphaned Positions
  7. Ghost Sell Fill Prevention
  8. IEEE Floating-Point Numerical Safety
  9. MTM Isolation from Settled Cash
  10. Equity Identity Invariance
"""

import copy
import pytest
from tests.scenarios.invariant_monitor import (
    InvariantCheckType,
    InvariantMonitor,
    PortfolioState,
)
from tests.scenarios.mock_market_factory import (
    MockMarketFactory,
    SyntheticEvent,
)
from tests.scenarios.runner import (
    ScenarioDefinition,
    ScenarioReport,
    ScenarioResult,
    ScenarioRunner,
)


@pytest.fixture
def runner() -> ScenarioRunner:
    return ScenarioRunner(strict_invariants=True)


@pytest.fixture
def monitor() -> InvariantMonitor:
    return InvariantMonitor(strict_mode=True)


def create_portfolio_state(user_id: str, balance: float = 10000.0, open_margin: float = 0.0) -> PortfolioState:
    free_cash = balance - open_margin
    return PortfolioState(
        user_id=user_id,
        settled_cash_usd=balance,
        free_cash_usd=free_cash,
        open_margin_usd=open_margin,
        high_water_mark_usd=balance,
        open_positions=[],
        closed_positions=[],
        total_realized_pnl_usd=0.0,
        total_unrealized_pnl_usd=0.0,
        equity_usd=balance,
    )


def create_mock_event(
    event_id: str,
    condition_id: str,
    side: str,
    price: float,
    notional: float,
    outcome: str = "Yes",
    category: str = "Crypto",
    block_num: int = 1000,
    log_idx: int = 0,
    tx_hash: str = "0xtx",
    wallet_addr: str = "0xWhale1",
    question: str = "Synthetic Test Market",
    event_type: str = "TRADE_LOG",
) -> SyntheticEvent:
    price = max(0.001, min(0.999, price))
    shares = round(notional / price, 4) if price > 0 else 0.0
    return SyntheticEvent(
        event_id=event_id,
        event_type=event_type,
        condition_id=condition_id,
        wallet_address=wallet_addr,
        side=side,
        price=price,
        notional_usd=round(notional, 2),
        shares=shares,
        tx_hash=tx_hash,
        log_index=log_idx,
        block_number=block_num,
        block_timestamp=float(block_num * 2.0),
        arrival_timestamp=float(block_num * 2.0 + 0.5),
        outcome=outcome,
        market_question=question,
        market_category=category,
    )


# ============================================================================
# TIER 1: ORDER BOOK & LIQUIDITY EXTREMES (55 Scenarios)
# ============================================================================

def build_tier_1_scenarios() -> list[ScenarioDefinition]:
    scenarios: list[ScenarioDefinition] = []

    # 1. Empty Book Scenarios (10 variations)
    for i in range(10):
        side = "BUY" if i % 2 == 0 else "SELL"
        outcome = "Yes" if i < 5 else "No"
        price = 0.10 * (i + 1)
        evt = create_mock_event(
            event_id=f"t1_empty_{i}",
            condition_id=f"0xcond_empty_{i}",
            side=side,
            price=price,
            notional=100.0,
            outcome=outcome,
            category="Crypto",
            block_num=1000 + i,
            log_idx=i,
            tx_hash=f"0xempty_{i}",
        )
        init_state = create_portfolio_state(f"u_empty_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T1_EMPTY_{i}",
            title=f"Empty Book {side} {outcome} @ {price:.2f}",
            tier="Tier 1: Order Book",
            description="Executes trade against completely empty order book depth",
            initial_state=init_state,
            order_book_factory=lambda: MockMarketFactory.create_empty_book("0xcond_empty", "Yes"),
            events=[evt],
        )
        scenarios.append(scen)

    # 2. Inverted & Crossed Spread Books (15 variations)
    for i in range(15):
        best_bid = round(0.60 + (i * 0.01), 4)
        best_ask = round(0.50 + (i * 0.01), 4)
        evt = create_mock_event(
            event_id=f"t1_inv_{i}",
            condition_id=f"0xcond_inv_{i}",
            side="BUY",
            price=best_ask,
            notional=50.0 + (i * 10.0),
            category="Politics",
            block_num=2000 + i,
            log_idx=i,
            tx_hash=f"0xinv_{i}",
        )
        init_state = create_portfolio_state(f"u_inv_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T1_INVERTED_{i}",
            title=f"Inverted Spread Book #{i} (Ask {best_ask:.2f} < Bid {best_bid:.2f})",
            tier="Tier 1: Order Book",
            description="Tests execution when ask is lower than bid due to crossed market feeds",
            initial_state=init_state,
            order_book_factory=lambda bb=best_bid, ba=best_ask: MockMarketFactory.create_inverted_book("0xcond_inv", "Yes", bb, ba),
            events=[evt],
        )
        scenarios.append(scen)

    # 3. Micro-Liquidity Depth Walks (15 variations)
    for i in range(15):
        liq_per_level = 0.50 + (i * 0.50)
        evt = create_mock_event(
            event_id=f"t1_micro_{i}",
            condition_id=f"0xcond_micro_{i}",
            side="BUY",
            price=0.50,
            notional=25.0 + (i * 5.0),
            category="Economics",
            block_num=3000 + i,
            log_idx=i,
            tx_hash=f"0xmicro_{i}",
        )
        init_state = create_portfolio_state(f"u_micro_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T1_MICRO_{i}",
            title=f"Micro Liquidity Depth Walk #{i} (${liq_per_level:.2f}/level)",
            tier="Tier 1: Order Book",
            description="Tests order book walking when individual price levels have sub-dollar liquidity",
            initial_state=init_state,
            order_book_factory=lambda: MockMarketFactory.create_micro_liquidity_book("0xcond_micro", "Yes", 0.50, 0.05),
            events=[evt],
        )
        scenarios.append(scen)

    # 4. Extreme Price Boundary Shocks (15 variations)
    for i in range(15):
        boundary_price = 0.01 if i < 5 else (0.99 if i < 10 else 0.005 * (i + 1))
        evt = create_mock_event(
            event_id=f"t1_shock_{i}",
            condition_id=f"0xcond_shock_{i}",
            side="BUY",
            price=boundary_price,
            notional=100.0,
            category="Crypto",
            block_num=4000 + i,
            log_idx=i,
            tx_hash=f"0xshock_{i}",
        )
        init_state = create_portfolio_state(f"u_shock_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T1_SHOCK_{i}",
            title=f"Price Boundary Shock #{i} @ {boundary_price:.4f}",
            tier="Tier 1: Order Book",
            description="Tests fee and sizing boundaries on extreme high/low probability contracts",
            initial_state=init_state,
            order_book_factory=lambda: MockMarketFactory.create_zero_spread_book("0xcond_shock", "Yes", 0.50),
            events=[evt],
        )
        scenarios.append(scen)

    return scenarios


# ============================================================================
# TIER 2: TIMING, NETWORK & SETTLEMENT DYNAMICS (55 Scenarios)
# ============================================================================

def build_tier_2_scenarios() -> list[ScenarioDefinition]:
    scenarios: list[ScenarioDefinition] = []

    # 1. Out-of-Order Block Arrivals (15 variations)
    for i in range(15):
        evt_buy = create_mock_event(event_id=f"t2_ooo_b_{i}", condition_id=f"0xcond_ooo_{i}", side="BUY", price=0.50, notional=100.0, block_num=5000 + i + 2, log_idx=0, tx_hash=f"0xooo_tx_b_{i}")
        evt_sell = create_mock_event(event_id=f"t2_ooo_a_{i}", condition_id=f"0xcond_ooo_{i}", side="SELL", price=0.60, notional=50.0, block_num=5000 + i, log_idx=1, tx_hash=f"0xooo_tx_a_{i}")
        init_state = create_portfolio_state(f"u_ooo_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T2_OOO_{i}",
            title=f"Out-of-Order Ingestion #{i}",
            tier="Tier 2: Timing/Network",
            description="Simulates network arrival where higher block precedes lower block log",
            initial_state=init_state,
            events=[evt_buy, evt_sell],
        )
        scenarios.append(scen)

    # 2. Duplicate Transaction Bursts & Idempotency (15 variations)
    for i in range(15):
        base_evt = create_mock_event(event_id=f"t2_dup_{i}", condition_id=f"0xcond_dup_{i}", side="BUY", price=0.50, notional=100.0, block_num=6000 + i, log_idx=2, tx_hash=f"0xdup_tx_{i}")
        dup_events = [copy.deepcopy(base_evt) for _ in range(3)]
        init_state = create_portfolio_state(f"u_dup_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T2_DUP_{i}",
            title=f"Duplicate Event Burst #{i} (3x Identical Tx)",
            tier="Tier 2: Timing/Network",
            description="Tests idempotency when identical logs arrive simultaneously across workers",
            initial_state=init_state,
            events=dup_events,
        )
        scenarios.append(scen)

    # 3. Binary Resolution Settlements (15 variations)
    for i in range(15):
        exit_price = 0.999 if i % 3 == 0 else (0.001 if i % 3 == 1 else 0.50)
        evt_in = create_mock_event(event_id=f"t2_res_in_{i}", condition_id=f"0xcond_res_{i}", side="BUY", price=0.40, notional=200.0, block_num=7000 + i, log_idx=0)
        evt_out = create_mock_event(event_id=f"t2_res_out_{i}", condition_id=f"0xcond_res_{i}", side="SELL", price=exit_price, notional=200.0, block_num=7000 + i + 100, log_idx=1)
        init_state = create_portfolio_state(f"u_res_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T2_RESOLUTION_{i}",
            title=f"Binary Market Resolution #{i} (Resolved to {exit_price:.3f})",
            tier="Tier 2: Timing/Network",
            description="Tests full settlement and PnL realization when contract resolves to binary bound",
            initial_state=init_state,
            events=[evt_in, evt_out],
        )
        scenarios.append(scen)

    # 4. Large Block-Lag Ingestion Catch-up (10 variations)
    for i in range(10):
        lag_blocks = 500 * (i + 1)
        evt = create_mock_event(event_id=f"t2_lag_{i}", condition_id=f"0xcond_lag_{i}", side="BUY", price=0.55, notional=150.0, block_num=10000 + lag_blocks, log_idx=0, category="Sports")
        init_state = create_portfolio_state(f"u_lag_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T2_LAG_{i}",
            title=f"Catch-up Stream #{i} (+{lag_blocks} blocks lag)",
            tier="Tier 2: Timing/Network",
            description="Tests ingestion stability when historical blocks stream in rapid succession",
            initial_state=init_state,
            events=[evt],
        )
        scenarios.append(scen)

    return scenarios


# ============================================================================
# TIER 3: COMPLEX POSITION & LIFECYCLE SEQUENCES (55 Scenarios)
# ============================================================================

def build_tier_3_scenarios() -> list[ScenarioDefinition]:
    scenarios: list[ScenarioDefinition] = []

    # 1. 1 Large BUY Closed by Multiple Partial SELLs (15 variations)
    for i in range(15):
        num_sells = 3 + (i % 5)
        buy_notional = 300.0 + (i * 20.0)
        sell_notional = round(buy_notional / num_sells, 2)
        events = [create_mock_event(event_id=f"t3_part_buy_{i}", condition_id=f"0xcond_fifo_1_{i}", side="BUY", price=0.40, notional=buy_notional, block_num=20000 + i, log_idx=0)]
        for s in range(num_sells):
            events.append(create_mock_event(event_id=f"t3_part_sell_{i}_{s}", condition_id=f"0xcond_fifo_1_{i}", side="SELL", price=0.45 + (s * 0.02), notional=sell_notional, block_num=20000 + i + (s + 1) * 10, log_idx=s + 1))

        init_state = create_portfolio_state(f"u_fifo_1_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T3_PARTIAL_SPLITS_{i}",
            title=f"1 Large BUY -> {num_sells} Partial SELLs (Total ${buy_notional:.2f})",
            tier="Tier 3: Lifecycle",
            description="Tests sequential FIFO lot splitting and conservation of notional/fee shares",
            initial_state=init_state,
            events=events,
        )
        scenarios.append(scen)

    # 2. Multiple BUY Lots Closed by 1 Large SELL (15 variations)
    for i in range(15):
        num_buys = 3 + (i % 4)
        lot_size = 50.0 + (i * 10.0)
        events = []
        for b in range(num_buys):
            events.append(create_mock_event(event_id=f"t3_m_buy_{i}_{b}", condition_id=f"0xcond_fifo_2_{i}", side="BUY", price=0.30 + (b * 0.05), notional=lot_size, block_num=21000 + i + b * 5, log_idx=b))
        total_buy_notional = num_buys * lot_size
        sell_notional = total_buy_notional - 25.0
        events.append(create_mock_event(event_id=f"t3_m_sell_{i}", condition_id=f"0xcond_fifo_2_{i}", side="SELL", price=0.60, notional=sell_notional, block_num=21000 + i + 100, log_idx=99))

        init_state = create_portfolio_state(f"u_fifo_2_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T3_MULTI_BUY_SINGLE_SELL_{i}",
            title=f"{num_buys} BUYs -> 1 Large SELL (${sell_notional:.2f} of ${total_buy_notional:.2f})",
            tier="Tier 3: Lifecycle",
            description="Tests chronological multi-lot iteration and closing without position orphans",
            initial_state=init_state,
            events=events,
        )
        scenarios.append(scen)

    # 3. Interleaved BUY/SELL Sequences on Single Market (15 variations)
    for i in range(15):
        events = [
            create_mock_event(event_id=f"t3_int_1_{i}", condition_id=f"0xcond_int_{i}", side="BUY", price=0.40, notional=100.0, block_num=22000+i, log_idx=0, category="Economics"),
            create_mock_event(event_id=f"t3_int_2_{i}", condition_id=f"0xcond_int_{i}", side="BUY", price=0.42, notional=150.0, block_num=22000+i+1, log_idx=1, category="Economics"),
            create_mock_event(event_id=f"t3_int_3_{i}", condition_id=f"0xcond_int_{i}", side="SELL", price=0.50, notional=120.0, block_num=22000+i+2, log_idx=2, category="Economics"),
            create_mock_event(event_id=f"t3_int_4_{i}", condition_id=f"0xcond_int_{i}", side="BUY", price=0.48, notional=80.0, block_num=22000+i+3, log_idx=3, category="Economics"),
            create_mock_event(event_id=f"t3_int_5_{i}", condition_id=f"0xcond_int_{i}", side="SELL", price=0.55, notional=150.0, block_num=22000+i+4, log_idx=4, category="Economics"),
        ]
        init_state = create_portfolio_state(f"u_int_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T3_INTERLEAVED_{i}",
            title=f"Interleaved 5-Trade Sequence #{i}",
            tier="Tier 3: Lifecycle",
            description="Tests alternating BUY and SELL orders on the same market condition",
            initial_state=init_state,
            events=events,
        )
        scenarios.append(scen)

    # 4. Multi-Condition Cross-Market Portfolios (10 variations)
    for i in range(10):
        events = []
        for c in range(4):
            events.append(create_mock_event(event_id=f"t3_cross_b_{i}_{c}", condition_id=f"0xcond_cross_{i}_{c}", side="BUY", price=0.35 + c*0.1, notional=100.0, block_num=23000+i+c, log_idx=c))
        for c in range(4):
            events.append(create_mock_event(event_id=f"t3_cross_s_{i}_{c}", condition_id=f"0xcond_cross_{i}_{c}", side="SELL", price=0.60, notional=100.0, block_num=23000+i+10+c, log_idx=10+c))

        init_state = create_portfolio_state(f"u_cross_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T3_CROSS_MARKET_{i}",
            title=f"4-Market Concurrent Portfolio #{i}",
            tier="Tier 3: Lifecycle",
            description="Simulates multi-position concurrent open and close cycles across distinct conditions",
            initial_state=init_state,
            events=events,
        )
        scenarios.append(scen)

    return scenarios


# ============================================================================
# TIER 4: MULTI-TENANCY & PORTFOLIO SCALING (55 Scenarios)
# ============================================================================

def build_tier_4_scenarios() -> list[ScenarioDefinition]:
    scenarios: list[ScenarioDefinition] = []

    # 1. Diverse Capital Sizing Scales ($50 to $500,000) (20 variations)
    for i in range(20):
        balance = round(50.0 * (1.5 ** i), 2)
        notional = round(min(max(5.0, balance * 0.10), 1000.0), 2)
        evt = create_mock_event(event_id=f"t4_scale_{i}", condition_id=f"0xcond_scale_{i}", side="BUY", price=0.50, notional=notional, block_num=30000 + i, log_idx=0)
        init_state = create_portfolio_state(f"u_scale_{i}", balance)
        scen = ScenarioDefinition(
            scenario_id=f"T4_CAPITAL_SCALE_{i}",
            title=f"Portfolio Sizing Scale #{i} (Balance ${balance:,.2f})",
            tier="Tier 4: Multi-Tenancy",
            description="Tests dynamic order sizing across micro-accounts and institutional balances",
            initial_state=init_state,
            events=[evt],
        )
        scenarios.append(scen)

    # 2. Risk Profile Limits (Conservative 5%, Balanced 10%, Aggressive 20%) (15 variations)
    for i in range(15):
        risk_pct = 0.05 if i % 3 == 0 else (0.10 if i % 3 == 1 else 0.20)
        profile_name = "Conservative" if risk_pct == 0.05 else ("Balanced" if risk_pct == 0.10 else "Aggressive")
        order_val = 10000.0 * risk_pct
        evt = create_mock_event(event_id=f"t4_risk_{i}", condition_id=f"0xcond_risk_{i}", side="BUY", price=0.45, notional=order_val, block_num=31000 + i, log_idx=0, category="Politics")
        init_state = create_portfolio_state(f"u_risk_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T4_RISK_PROFILE_{i}",
            title=f"{profile_name} Risk Profile #{i} (${order_val:.2f} max cap)",
            tier="Tier 4: Multi-Tenancy",
            description="Tests risk profile allocation caps and margin reservations",
            initial_state=init_state,
            events=[evt],
        )
        scenarios.append(scen)

    # 3. High-Water Mark Ratchet Cycles (Profit -> Drawdown -> Recovery) (10 variations)
    for i in range(10):
        events = [
            create_mock_event(event_id=f"t4_hwm_1_{i}", condition_id=f"0xcond_hwm_{i}_1", side="BUY", price=0.40, notional=500.0, block_num=32000+i, log_idx=0),
            create_mock_event(event_id=f"t4_hwm_2_{i}", condition_id=f"0xcond_hwm_{i}_1", side="SELL", price=0.60, notional=500.0, block_num=32000+i+1, log_idx=1),
            create_mock_event(event_id=f"t4_hwm_3_{i}", condition_id=f"0xcond_hwm_{i}_2", side="BUY", price=0.60, notional=500.0, block_num=32000+i+2, log_idx=2),
            create_mock_event(event_id=f"t4_hwm_4_{i}", condition_id=f"0xcond_hwm_{i}_2", side="SELL", price=0.40, notional=500.0, block_num=32000+i+3, log_idx=3),
        ]
        init_state = create_portfolio_state(f"u_hwm_{i}", 10000.0)
        scen = ScenarioDefinition(
            scenario_id=f"T4_HWM_RATCHET_{i}",
            title=f"HWM Profit-Loss Ratchet Cycle #{i}",
            tier="Tier 4: Multi-Tenancy",
            description="Verifies that High-Water Mark strictly ratchets up and never declines during loss",
            initial_state=init_state,
            events=events,
        )
        scenarios.append(scen)

    # 4. Zero-Cash & Maximum Leverage Ceiling Guards (10 variations)
    for i in range(10):
        evt = create_mock_event(event_id=f"t4_margin_guard_{i}", condition_id=f"0xcond_margin_guard_{i}", side="BUY", price=0.50, notional=500.0, block_num=33000 + i, log_idx=0)
        init_state = create_portfolio_state(f"u_margin_guard_{i}", 50.0)
        scen = ScenarioDefinition(
            scenario_id=f"T4_MARGIN_GUARD_{i}",
            title=f"Zero-Cash Ceiling Guard #{i} ($500 order on $50 cash)",
            tier="Tier 4: Multi-Tenancy",
            description="Verifies that orders exceeding settled cash are rejected to prevent negative cash",
            initial_state=init_state,
            events=[evt],
        )
        scenarios.append(scen)

    return scenarios


def get_all_220_scenarios() -> list[ScenarioDefinition]:
    return (
        build_tier_1_scenarios()
        + build_tier_2_scenarios()
        + build_tier_3_scenarios()
        + build_tier_4_scenarios()
    )


# ============================================================================
# PYTEST SUITE EXECUTION
# ============================================================================

def test_tier_1_order_book_extremes(runner: ScenarioRunner):
    scenarios = build_tier_1_scenarios()
    assert len(scenarios) == 55
    report = runner.run_matrix(scenarios)
    assert report.failed_scenarios == 0, f"Tier 1 failures: {[r for r in report.results if not r.passed]}"
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0


def test_tier_2_network_and_settlement_dynamics(runner: ScenarioRunner):
    scenarios = build_tier_2_scenarios()
    assert len(scenarios) == 55
    report = runner.run_matrix(scenarios)
    assert report.failed_scenarios == 0, f"Tier 2 failures: {[r for r in report.results if not r.passed]}"
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0


def test_tier_3_position_lifecycle_sequences(runner: ScenarioRunner):
    scenarios = build_tier_3_scenarios()
    assert len(scenarios) == 55
    report = runner.run_matrix(scenarios)
    assert report.failed_scenarios == 0, f"Tier 3 failures: {[r for r in report.results if not r.passed]}"
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0


def test_tier_4_multi_tenancy_and_portfolio_scaling(runner: ScenarioRunner):
    scenarios = build_tier_4_scenarios()
    assert len(scenarios) == 55
    report = runner.run_matrix(scenarios)
    assert report.failed_scenarios == 0, f"Tier 4 failures: {[r for r in report.results if not r.passed]}"
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0


def test_full_220_scenario_stress_matrix_aggregate(runner: ScenarioRunner):
    scenarios = get_all_220_scenarios()
    assert len(scenarios) == 220
    report = runner.run_matrix(scenarios)
    print("\n" + report.summary())
    assert report.total_scenarios == 220
    assert report.passed_scenarios == 220
    assert report.failed_scenarios == 0
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0
