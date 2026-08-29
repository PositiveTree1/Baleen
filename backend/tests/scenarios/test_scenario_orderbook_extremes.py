"""
Baleen Scenario Stress Matrix — Suite 1: Order Book & Liquidity Extremes.

Contains 55 distinct operational and market scenarios stressing:
  - S001-S010: Empty books, empty bids, empty asks, zero-liquidity fallbacks.
  - S011-S020: Crossed/Inverted books, negative spreads, zero-spread top of book.
  - S021-S030: Micro-liquidity ($0.01 depth), single-share levels, sub-penny dust.
  - S031-S040: Whale order execution, multi-level sweeps, deep book exhaustion ($1M+ sweeps).
  - S041-S050: Extreme price shocks (0.99 to 0.01, 0.01 to 0.99, flash crashes, binary extremes).
  - S051-S055: Zero-price contracts ($p=0.00$), ceiling contracts ($p=1.00$), and boundary fee quantization.

All scenarios execute through InvariantMonitor validation to guarantee:
  1. Cash Non-Negativity
  2. Settled Cash - Open Margin Conservation
  3. High-Water Mark Monotonicity
  4. FIFO Lot Splitting Conservation
  5. Polymarket Quadratic Fee Bounds (Theta in [0.00, 0.072])
  6. Zero Orphaned Positions
  7. Ghost Sell Fill Prevention
  8. IEEE Floating-Point Numerical Safety
  9. MTM Isolation from Settled Cash
  10. Equity Identity Invariance
"""

import copy
import pytest
from app.sizing.fill_simulator import simulate_fill
from tests.scenarios.invariant_monitor import (
    InvariantCheckType,
    InvariantMonitor,
    PortfolioState,
    PositionLot,
    TradeExecution,
)
from tests.scenarios.mock_market_factory import (
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
def runner() -> ScenarioRunner:
    return ScenarioRunner(strict_invariants=True)


@pytest.fixture
def monitor() -> InvariantMonitor:
    return InvariantMonitor(strict_mode=True)


def create_state(user_id: str, balance: float = 10000.0, open_margin: float = 0.0) -> PortfolioState:
    free_cash = max(0.0, balance - open_margin)
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


def create_event(
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
# SCENARIO BUILDER: 55 DISTINCT ORDER BOOK EXTREMES SCENARIOS
# ============================================================================

def build_orderbook_extremes_scenarios() -> list[ScenarioDefinition]:
    scenarios: list[ScenarioDefinition] = []

    # ------------------------------------------------------------------------
    # S001 - S010: Empty Books & Zero Liquidity Fallbacks (10 Scenarios)
    # ------------------------------------------------------------------------
    # S001: Completely empty book BUY attempt
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S001_EMPTY_BOOK_BUY",
            title="Empty Book BUY Fill Simulation Fallback",
            tier="Tier 1: Order Book",
            description="Simulates BUY attempt on completely empty book (0 bids, 0 asks) ensuring zero cash leakage",
            initial_state=create_state("u_s001", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_book("0xcond_empty_buy", "Yes"),
            events=[create_event("evt_s001", "0xcond_empty_buy", "BUY", 0.50, 100.0)],
        )
    )
    # S002: Completely empty book SELL attempt (Ghost sell guard)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S002_EMPTY_BOOK_SELL",
            title="Empty Book SELL Zero-Held Guard",
            tier="Tier 1: Order Book",
            description="Simulates SELL on empty book with 0 held positions ensuring ghost sell rejection",
            initial_state=create_state("u_s002", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_book("0xcond_empty_sell", "Yes"),
            events=[create_event("evt_s002", "0xcond_empty_sell", "SELL", 0.50, 100.0)],
        )
    )
    # S003: Empty bids book, BUY attempt (valid asks available)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S003_EMPTY_BIDS_BUY",
            title="Empty Bids Book BUY Execution",
            tier="Tier 1: Order Book",
            description="Executes BUY against book with 0 bids but active ask liquidity",
            initial_state=create_state("u_s003", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_bids_book("0xcond_empty_bids", "Yes", 0.50),
            events=[create_event("evt_s003", "0xcond_empty_bids", "BUY", 0.52, 100.0)],
        )
    )
    # S004: Empty bids book, SELL attempt
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S004_EMPTY_BIDS_SELL",
            title="Empty Bids Book SELL Attempt",
            tier="Tier 1: Order Book",
            description="Attempts SELL against 0 bids book; verify fill simulator returns 0 fill without crash",
            initial_state=create_state("u_s004", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_bids_book("0xcond_empty_bids_sell", "Yes", 0.50),
            events=[create_event("evt_s004", "0xcond_empty_bids_sell", "SELL", 0.50, 50.0)],
        )
    )
    # S005: Empty asks book, BUY attempt
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S005_EMPTY_ASKS_BUY",
            title="Empty Asks Book BUY Attempt",
            tier="Tier 1: Order Book",
            description="Attempts BUY against 0 asks book; verify fill simulator returns 0 fill without crash",
            initial_state=create_state("u_s005", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_asks_book("0xcond_empty_asks", "Yes", 0.50),
            events=[create_event("evt_s005", "0xcond_empty_asks", "BUY", 0.50, 100.0)],
        )
    )
    # S006: Empty asks book, SELL execution (valid bids available)
    init_state_s006 = create_state("u_s006", 10000.0)
    init_lot_s006 = PositionLot("lot_s006", "0xcond_empty_asks_sell", "Yes", "BUY", 0.45, 222.22, 100.0, 3.60, "FILLED", "u_s006")
    init_state_s006.open_positions.append(init_lot_s006)
    init_state_s006.open_margin_usd = 100.0
    init_state_s006.free_cash_usd = 9900.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S006_EMPTY_ASKS_SELL",
            title="Empty Asks Book SELL Liquidation",
            tier="Tier 1: Order Book",
            description="Executes valid SELL liquidation against bids when asks are completely empty",
            initial_state=init_state_s006,
            order_book_factory=lambda: MockMarketFactory.create_empty_asks_book("0xcond_empty_asks_sell", "Yes", 0.50),
            events=[create_event("evt_s006", "0xcond_empty_asks_sell", "SELL", 0.48, 100.0)],
        )
    )
    # S007: Empty book with low-price limit order ($p=0.001)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S007_EMPTY_BOOK_LOW_PRICE",
            title="Empty Book Extreme Low-Price Boundary ($0.001)",
            tier="Tier 1: Order Book",
            description="Validates non-division-by-zero on empty book at lowest limit bound",
            initial_state=create_state("u_s007", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_book("0xcond_empty_low", "Yes"),
            events=[create_event("evt_s007", "0xcond_empty_low", "BUY", 0.001, 10.0)],
        )
    )
    # S008: Empty book with high-price limit order ($p=0.999)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S008_EMPTY_BOOK_HIGH_PRICE",
            title="Empty Book Extreme High-Price Boundary ($0.999)",
            tier="Tier 1: Order Book",
            description="Validates ceiling fee bounds and non-overflow on empty book at ceiling price",
            initial_state=create_state("u_s008", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_book("0xcond_empty_high", "Yes"),
            events=[create_event("evt_s008", "0xcond_empty_high", "BUY", 0.999, 100.0)],
        )
    )
    # S009: Empty book on 'No' outcome contract
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S009_EMPTY_BOOK_NO_OUTCOME",
            title="Empty Book on Opposing 'No' Outcome",
            tier="Tier 1: Order Book",
            description="Tests empty order book handling specifically on complementary 'No' share side",
            initial_state=create_state("u_s009", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_book("0xcond_empty_no", "No"),
            events=[create_event("evt_s009", "0xcond_empty_no", "BUY", 0.50, 100.0, outcome="No")],
        )
    )
    # S010: Zero-liquidity fallback consecutive retry sweeps
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S010_ZERO_LIQUIDITY_RETRY_SWEEPS",
            title="Zero Liquidity 5-Step Consecutive Retry Sweep",
            tier="Tier 1: Order Book",
            description="Executes 5 rapid consecutive trades against zero liquidity without state drift",
            initial_state=create_state("u_s010", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_empty_book("0xcond_empty_sweep", "Yes"),
            events=[
                create_event(f"evt_s010_{i}", "0xcond_empty_sweep", "BUY", 0.50, 50.0, block_num=1000 + i, log_idx=i)
                for i in range(5)
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S011 - S020: Crossed/Inverted Books & Zero Spread (10 Scenarios)
    # ------------------------------------------------------------------------
    # S011: Standard inverted book BUY (Ask 0.55 < Bid 0.65)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S011_INVERTED_BOOK_BUY",
            title="Inverted Spread Book BUY Execution",
            tier="Tier 1: Order Book",
            description="Tests BUY execution against crossed market feeds where best ask is lower than best bid",
            initial_state=create_state("u_s011", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_inv_1", "Yes", 0.65, 0.55),
            events=[create_event("evt_s011", "0xcond_inv_1", "BUY", 0.55, 100.0)],
        )
    )
    # S012: Inverted book SELL execution
    init_state_s012 = create_state("u_s012", 10000.0)
    init_state_s012.open_positions.append(PositionLot("lot_s012", "0xcond_inv_2", "Yes", "BUY", 0.50, 200.0, 100.0, 3.60, "FILLED", "u_s012"))
    init_state_s012.open_margin_usd = 100.0
    init_state_s012.free_cash_usd = 9900.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S012_INVERTED_BOOK_SELL",
            title="Inverted Spread Book SELL Execution",
            tier="Tier 1: Order Book",
            description="Tests SELL execution into crossed book best bid (0.65) realizing clean profit",
            initial_state=init_state_s012,
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_inv_2", "Yes", 0.65, 0.55),
            events=[create_event("evt_s012", "0xcond_inv_2", "SELL", 0.65, 100.0)],
        )
    )
    # S013: Zero-spread top of book (Bid 0.50 == Ask 0.50)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S013_ZERO_SPREAD_BOOK",
            title="Zero Spread Top of Book Execution",
            tier="Tier 1: Order Book",
            description="Validates execution when spread is exactly 0.00 cents",
            initial_state=create_state("u_s013", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_zero_spread_book("0xcond_zs", "Yes", 0.50),
            events=[create_event("evt_s013", "0xcond_zs", "BUY", 0.50, 150.0)],
        )
    )
    # S014: Severely crossed book (Bid 0.80 > Ask 0.20)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S014_SEVERELY_CROSSED_BOOK",
            title="Severely Crossed Book Arbitrage Boundary (Bid 0.80 > Ask 0.20)",
            tier="Tier 1: Order Book",
            description="Tests stability when order book has 60 cent negative spread",
            initial_state=create_state("u_s014", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_sev_cross", "Yes", 0.80, 0.20),
            events=[create_event("evt_s014", "0xcond_sev_cross", "BUY", 0.20, 200.0)],
        )
    )
    # S015: Inverted book with asymmetric heavy bid depth
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S015_INVERTED_HEAVY_BID",
            title="Inverted Book with Asymmetric Heavy Bid Depth",
            tier="Tier 1: Order Book",
            description="Tests inverted book with $50k bid depth and $100 ask depth",
            initial_state=create_state("u_s015", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_inv_hbid", "Yes", 0.60, 0.52),
            events=[create_event("evt_s015", "0xcond_inv_hbid", "BUY", 0.52, 100.0)],
        )
    )
    # S016: Inverted book with asymmetric heavy ask depth
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S016_INVERTED_HEAVY_ASK",
            title="Inverted Book with Asymmetric Heavy Ask Depth",
            tier="Tier 1: Order Book",
            description="Tests inverted book with $100 bid depth and $50k ask depth",
            initial_state=create_state("u_s016", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_inv_hask", "Yes", 0.58, 0.50),
            events=[create_event("evt_s016", "0xcond_inv_hask", "BUY", 0.50, 500.0)],
        )
    )
    # S017: Multi-level crossed book (3 crossed tiers)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S017_MULTI_LEVEL_CROSSED",
            title="Multi-Level Crossed Order Book (3 Inverted Tiers)",
            tier="Tier 1: Order Book",
            description="Tests walking multiple inverted price levels without sort corruption",
            initial_state=create_state("u_s017", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_m_cross", "Yes", 0.70, 0.50, depth=5),
            events=[create_event("evt_s017", "0xcond_m_cross", "BUY", 0.52, 250.0)],
        )
    )
    # S018: Crossed book on high-probability contract ($p=0.92$)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S018_CROSSED_HIGH_PROB",
            title="Crossed Spread on High-Probability Contract ($p=0.92$)",
            tier="Tier 1: Order Book",
            description="Tests fee calculation at upper probability ceiling with inverted spread",
            initial_state=create_state("u_s018", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_cross_hp", "Yes", 0.95, 0.90),
            events=[create_event("evt_s018", "0xcond_cross_hp", "BUY", 0.90, 100.0)],
        )
    )
    # S019: Crossed book on low-probability contract ($p=0.08$)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S019_CROSSED_LOW_PROB",
            title="Crossed Spread on Low-Probability Contract ($p=0.08$)",
            tier="Tier 1: Order Book",
            description="Tests fee calculation at lower probability floor with inverted spread",
            initial_state=create_state("u_s019", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_inverted_book("0xcond_cross_lp", "Yes", 0.12, 0.08),
            events=[create_event("evt_s019", "0xcond_cross_lp", "BUY", 0.08, 100.0)],
        )
    )
    # S020: Rapid crossed to normal book flip sequence
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S020_CROSSED_FLIP_CYCLE",
            title="Rapid Inversion Flip Cycle (Crossed -> Normal -> Crossed)",
            tier="Tier 1: Order Book",
            description="Tests 3 sequential trades transitioning from crossed to balanced market state",
            initial_state=create_state("u_s020", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_flip", "Yes", 0.50),
            events=[
                create_event("evt_s020_1", "0xcond_flip", "BUY", 0.48, 100.0, block_num=2000, log_idx=0),
                create_event("evt_s020_2", "0xcond_flip", "BUY", 0.50, 100.0, block_num=2001, log_idx=1),
                create_event("evt_s020_3", "0xcond_flip", "BUY", 0.52, 100.0, block_num=2002, log_idx=2),
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S021 - S030: Micro-Liquidity, Sub-Penny Ticks & Odd Lots (10 Scenarios)
    # ------------------------------------------------------------------------
    # S021: Micro-liquidity $0.01 depth BUY sweep
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S021_MICRO_LIQUIDITY_BUY",
            title="Micro-Liquidity ($0.01 Depth) BUY Exhaustion",
            tier="Tier 1: Order Book",
            description="Simulates BUY that exhausts entire $0.01 micro-liquidity book depth",
            initial_state=create_state("u_s021", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_micro_liquidity_book("0xcond_micro_b", "Yes", 0.50, 0.01),
            events=[create_event("evt_s021", "0xcond_micro_b", "BUY", 0.51, 50.0)],
        )
    )
    # S022: Micro-liquidity $0.01 depth SELL sweep
    init_s022 = create_state("u_s022", 10000.0)
    init_s022.open_positions.append(PositionLot("lot_s022", "0xcond_micro_s", "Yes", "BUY", 0.50, 100.0, 50.0, 1.80, "FILLED", "u_s022"))
    init_s022.open_margin_usd = 50.0
    init_s022.free_cash_usd = 9950.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S022_MICRO_LIQUIDITY_SELL",
            title="Micro-Liquidity ($0.01 Depth) SELL Exhaustion",
            tier="Tier 1: Order Book",
            description="Simulates SELL into $0.01 bids book with partial closure and lot splitting",
            initial_state=init_s022,
            order_book_factory=lambda: MockMarketFactory.create_micro_liquidity_book("0xcond_micro_s", "Yes", 0.50, 0.01),
            events=[create_event("evt_s022", "0xcond_micro_s", "SELL", 0.49, 25.0)],
        )
    )
    # S023: Sub-penny granular ticks ($0.48555 bid, $0.51444 ask)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S023_SUBPENNY_TICKS",
            title="Granular Sub-Penny Tick Pricing ($0.48555 / $0.51444)",
            tier="Tier 1: Order Book",
            description="Verifies floating point quantization and fee rounding on sub-penny prices",
            initial_state=create_state("u_s023", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_subpenny_dust_book("0xcond_subpenny", "Yes"),
            events=[create_event("evt_s023", "0xcond_subpenny", "BUY", 0.51444, 123.45)],
        )
    )
    # S024: Single share levels (1 share per level)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S024_SINGLE_SHARE_LEVELS",
            title="Single-Share Level Order Book Exhaustion",
            tier="Tier 1: Order Book",
            description="Tests depth consumption when each price level contains exactly 1.0 share",
            initial_state=create_state("u_s024", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_single_sh", "Yes", 0.50, depth=10, total_liquidity_usd=10.0),
            events=[create_event("evt_s024", "0xcond_single_sh", "BUY", 0.50, 20.0)],
        )
    )
    # S025: Ultra-dust tick sizes ($0.0001 per share)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S025_ULTRA_DUST_TICKS",
            title="Ultra-Dust Tick Sizes ($0.0001)",
            tier="Tier 1: Order Book",
            description="Verifies non-zero division and exact cent fee lower bounds on dust ticks",
            initial_state=create_state("u_s025", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_dust", "Yes", 0.50),
            events=[create_event("evt_s025", "0xcond_dust", "BUY", 0.5001, 10.0)],
        )
    )
    # S026: Micro-liquidity with high slippage penalty
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S026_MICRO_HIGH_SLIPPAGE",
            title="Micro-Liquidity Heavy Slippage Penalty",
            tier="Tier 1: Order Book",
            description="Verifies slippage calculation bounded at theoretical limits on shallow books",
            initial_state=create_state("u_s026", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_micro_liquidity_book("0xcond_slip", "Yes", 0.50, 0.05),
            events=[create_event("evt_s026", "0xcond_slip", "BUY", 0.55, 100.0)],
        )
    )
    # S027: Micro-liquidity on 'No' outcome
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S027_MICRO_NO_OUTCOME",
            title="Micro-Liquidity on 'No' Outcome Contract",
            tier="Tier 1: Order Book",
            description="Tests micro-liquidity execution on complementary 'No' share outcome",
            initial_state=create_state("u_s027", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_micro_liquidity_book("0xcond_micro_no", "No", 0.50, 0.02),
            events=[create_event("evt_s027", "0xcond_micro_no", "BUY", 0.50, 50.0, outcome="No")],
        )
    )
    # S028: Multi-level sub-penny staircase depth
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S028_SUBPENNY_STAIRCASE",
            title="Multi-Level Sub-Penny Staircase Depth",
            tier="Tier 1: Order Book",
            description="Tests multi-level sub-penny depth consumption across 10 granular increments",
            initial_state=create_state("u_s028", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_stair", "Yes", 0.50, spread=0.005, depth=10),
            events=[create_event("evt_s028", "0xcond_stair", "BUY", 0.51, 150.0)],
        )
    )
    # S029: Micro-liquidity with uneven odd-lot sizes
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S029_ODD_LOT_SIZES",
            title="Micro-Liquidity Uneven Odd-Lot Sizes (3.1415, 2.7182 shares)",
            tier="Tier 1: Order Book",
            description="Verifies fractional share rounding conservation on irrational/odd lot sizes",
            initial_state=create_state("u_s029", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_subpenny_dust_book("0xcond_odd", "Yes"),
            events=[create_event("evt_s029", "0xcond_odd", "BUY", 0.51, 77.77)],
        )
    )
    # S030: Sub-penny rounding boundary at $0.00005 cents
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S030_HALF_CENT_ROUNDING_BOUNDARY",
            title="Sub-Penny Half-Cent Rounding Boundary ($0.00005)",
            tier="Tier 1: Order Book",
            description="Tests half-to-even vs standard round conservation across fee splits",
            initial_state=create_state("u_s030", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_half_cent", "Yes", 0.50005),
            events=[create_event("evt_s030", "0xcond_half_cent", "BUY", 0.50005, 100.0)],
        )
    )

    # ------------------------------------------------------------------------
    # S031 - S040: Whale Orders & Deep Book Sweeps (10 Scenarios)
    # ------------------------------------------------------------------------
    # S031: $50,000 whale sweep across 10 levels
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S031_WHALE_SWEEP_50K",
            title="$50,000 Whale Order Sweep across 10 Levels",
            tier="Tier 1: Order Book",
            description="Simulates $50,000 institutional BUY order consuming multiple depth tiers",
            initial_state=create_state("u_s031", 100000.0),
            order_book_factory=lambda: MockMarketFactory.create_whale_depth_book("0xcond_whale_50k", "Yes", 0.50, 1000000.0, 20),
            events=[create_event("evt_s031", "0xcond_whale_50k", "BUY", 0.52, 50000.0)],
        )
    )
    # S032: $100,000 whale sweep across 20 levels
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S032_WHALE_SWEEP_100K",
            title="$100,000 Whale Order Sweep across 20 Levels",
            tier="Tier 1: Order Book",
            description="Simulates $100,000 order sweeping 20 book levels with non-linear slippage",
            initial_state=create_state("u_s032", 200000.0),
            order_book_factory=lambda: MockMarketFactory.create_whale_depth_book("0xcond_whale_100k", "Yes", 0.50, 1000000.0, 20),
            events=[create_event("evt_s032", "0xcond_whale_100k", "BUY", 0.55, 100000.0)],
        )
    )
    # S033: $500,000 mega-whale sweep deep book exhaustion
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S033_WHALE_SWEEP_500K",
            title="$500,000 Mega-Whale Sweep Deep Book Exhaustion",
            tier="Tier 1: Order Book",
            description="Tests massive 500k sweep consuming 50% of available book depth",
            initial_state=create_state("u_s033", 1000000.0),
            order_book_factory=lambda: MockMarketFactory.create_whale_depth_book("0xcond_whale_500k", "Yes", 0.50, 1000000.0, 20),
            events=[create_event("evt_s033", "0xcond_whale_500k", "BUY", 0.60, 500000.0)],
        )
    )
    # S034: $1,000,000 full book absorption
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S034_WHALE_SWEEP_1M",
            title="$1,000,000 Full Book Absorption Sweep",
            tier="Tier 1: Order Book",
            description="Consumes 100% of available ask side liquidity with full fee conservation",
            initial_state=create_state("u_s034", 2000000.0),
            order_book_factory=lambda: MockMarketFactory.create_whale_depth_book("0xcond_whale_1m", "Yes", 0.50, 1000000.0, 20),
            events=[create_event("evt_s034", "0xcond_whale_1m", "BUY", 0.65, 1000000.0)],
        )
    )
    # S035: Asymmetric whale BUY draining asks to $0.99
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S035_WHALE_DRAIN_TO_CEILING",
            title="Asymmetric Whale BUY Draining Asks to $0.99",
            tier="Tier 1: Order Book",
            description="Pushes market price to 0.99 boundary; checks quadratic fee capping at 0.072",
            initial_state=create_state("u_s035", 50000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_drain_ceil", "Yes", 0.50, depth=10, total_liquidity_usd=20000.0),
            events=[create_event("evt_s035", "0xcond_drain_ceil", "BUY", 0.98, 25000.0)],
        )
    )
    # S036: Asymmetric whale SELL crashing bids to $0.01
    init_s036 = create_state("u_s036", 50000.0)
    init_s036.open_positions.append(PositionLot("lot_s036", "0xcond_drain_floor", "Yes", "BUY", 0.50, 50000.0, 25000.0, 900.0, "FILLED", "u_s036"))
    init_s036.open_margin_usd = 25000.0
    init_s036.free_cash_usd = 25000.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S036_WHALE_CRASH_TO_FLOOR",
            title="Asymmetric Whale SELL Crashing Bids to $0.01",
            tier="Tier 1: Order Book",
            description="Liquidates 25k position into thin bids crashing market to 0.01 floor",
            initial_state=init_s036,
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_drain_floor", "Yes", 0.50, depth=10, total_liquidity_usd=20000.0),
            events=[create_event("evt_s036", "0xcond_drain_floor", "SELL", 0.02, 25000.0)],
        )
    )
    # S037: Whale sweep with partial fill remainder
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S037_WHALE_PARTIAL_REMAINDER",
            title="Whale Sweep with Partial Fill Unfilled Remainder",
            tier="Tier 1: Order Book",
            description="Verifies unspent cash remains safely in settled cash when order partially fills",
            initial_state=create_state("u_s037", 50000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_part_rem", "Yes", 0.50, total_liquidity_usd=10000.0),
            events=[create_event("evt_s037", "0xcond_part_rem", "BUY", 0.55, 30000.0)],
        )
    )
    # S038: Dual simultaneous whale orders on opposing sides
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S038_DUAL_WHALE_OPPOSING",
            title="Dual Simultaneous Whale Orders on Opposing Sides",
            tier="Tier 1: Order Book",
            description="Simulates $20,000 BUY followed immediately by $20,000 BUY on 'No' outcome",
            initial_state=create_state("u_s038", 100000.0),
            order_book_factory=lambda: MockMarketFactory.create_whale_depth_book("0xcond_dual_whale", "Yes", 0.50, 500000.0),
            events=[
                create_event("evt_s038_1", "0xcond_dual_whale", "BUY", 0.50, 20000.0, outcome="Yes", block_num=3000, log_idx=0),
                create_event("evt_s038_2", "0xcond_dual_whale", "BUY", 0.50, 20000.0, outcome="No", block_num=3000, log_idx=1),
            ],
        )
    )
    # S039: Whale sweep triggering max slippage guard
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S039_MAX_SLIPPAGE_GUARD",
            title="Whale Sweep Max Slippage Circuit Breaker",
            tier="Tier 1: Order Book",
            description="Tests slippage calculation when order exceeds available liquidity depth",
            initial_state=create_state("u_s039", 50000.0),
            order_book_factory=lambda: MockMarketFactory.create_micro_liquidity_book("0xcond_slip_max", "Yes", 0.50, 1.0),
            events=[create_event("evt_s039", "0xcond_slip_max", "BUY", 0.60, 10000.0)],
        )
    )
    # S040: Institutional deep book multi-tier execution
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S040_INSTITUTIONAL_MULTI_TIER",
            title="Institutional Deep Book Multi-Tier Execution ($250k Sweep)",
            tier="Tier 1: Order Book",
            description="Validates multi-tier fill simulator accuracy across 20 depth levels",
            initial_state=create_state("u_s040", 500000.0),
            order_book_factory=lambda: MockMarketFactory.create_whale_depth_book("0xcond_inst", "Yes", 0.50, 2000000.0, 20),
            events=[create_event("evt_s040", "0xcond_inst", "BUY", 0.54, 250000.0)],
        )
    )

    # ------------------------------------------------------------------------
    # S041 - S050: Extreme Price Shocks & Flash Crashes (10 Scenarios)
    # ------------------------------------------------------------------------
    # S041: Flash crash 0.99 -> 0.01 instant collapse
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S041_FLASH_CRASH_INSTANT",
            title="Flash Crash 0.99 -> 0.01 Instant Collapse",
            tier="Tier 1: Order Book",
            description="Simulates 98-cent instantaneous price collapse; checks fee and margin stability",
            initial_state=create_state("u_s041", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_price_shock_book("0xcond_crash_inst", "Yes", 0.99, 0.01, "crash"),
            events=[create_event("evt_s041", "0xcond_crash_inst", "BUY", 0.01, 100.0)],
        )
    )
    # S042: Parabolic spike 0.01 -> 0.99 instant rally
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S042_PARABOLIC_RALLY_INSTANT",
            title="Parabolic Rally 0.01 -> 0.99 Instant Spike",
            tier="Tier 1: Order Book",
            description="Simulates 98-cent instantaneous rally; verifies quadratic fee clamping at 0.072",
            initial_state=create_state("u_s042", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_price_shock_book("0xcond_rally_inst", "Yes", 0.01, 0.99, "rally"),
            events=[create_event("evt_s042", "0xcond_rally_inst", "BUY", 0.99, 100.0)],
        )
    )
    # S043: Oscillating flash crash/rally (0.90 -> 0.10 -> 0.90)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S043_OSCILLATING_FLASH_CYCLE",
            title="Oscillating Flash Crash and Recovery (0.90 -> 0.10 -> 0.90)",
            tier="Tier 1: Order Book",
            description="Tests state machine stability across extreme price oscillation cycle",
            initial_state=create_state("u_s043", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_osc", "Yes", 0.50),
            events=[
                create_event("evt_s043_1", "0xcond_osc", "BUY", 0.90, 100.0, block_num=4000, log_idx=0),
                create_event("evt_s043_2", "0xcond_osc", "BUY", 0.10, 100.0, block_num=4001, log_idx=1),
                create_event("evt_s043_3", "0xcond_osc", "BUY", 0.90, 100.0, block_num=4002, log_idx=2),
            ],
        )
    )
    # S044: Flash crash on 'Yes' with inverse rally on 'No'
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S044_INVERSE_PAIR_SHOCK",
            title="Flash Shock with Inverse 'No' Outcome Rally",
            tier="Tier 1: Order Book",
            description="Validates complementary outcome conservation during extreme shock",
            initial_state=create_state("u_s044", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_inv_pair", "Yes", 0.10),
            events=[
                create_event("evt_s044_1", "0xcond_inv_pair", "BUY", 0.05, 100.0, outcome="Yes", block_num=4100, log_idx=0),
                create_event("evt_s044_2", "0xcond_inv_pair", "BUY", 0.95, 100.0, outcome="No", block_num=4101, log_idx=1),
            ],
        )
    )
    # S045: Price shock during active held open position
    init_s045 = create_state("u_s045", 10000.0)
    init_s045.open_positions.append(PositionLot("lot_s045", "0xcond_shock_held", "Yes", "BUY", 0.85, 235.29, 200.0, 7.20, "FILLED", "u_s045"))
    init_s045.open_margin_usd = 200.0
    init_s045.free_cash_usd = 9800.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S045_SHOCK_WITH_HELD_POSITION",
            title="Price Shock on Existing Active Position (0.85 -> 0.15)",
            tier="Tier 1: Order Book",
            description="Tests MTM drawdown calculation without illegal settled cash leakage",
            initial_state=init_s045,
            order_book_factory=lambda: MockMarketFactory.create_price_shock_book("0xcond_shock_held", "Yes", 0.85, 0.15, "crash"),
            events=[create_event("evt_s045", "0xcond_shock_held", "SELL", 0.15, 100.0)],
        )
    )
    # S046: Flash crash triggering MTM drawdown and margin verification
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S046_CRASH_MARGIN_VERIFICATION",
            title="Flash Crash Drawdown and Margin Equality Verification",
            tier="Tier 1: Order Book",
            description="Verifies Free Cash == max(0, Settled - Margin) during 80% market drop",
            initial_state=create_state("u_s046", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_crash_marg", "Yes", 0.20),
            events=[create_event("evt_s046", "0xcond_crash_marg", "BUY", 0.20, 500.0)],
        )
    )
    # S047: Parabolic rally triggering HWM ratchet
    init_s047 = create_state("u_s047", 10000.0)
    init_s047.open_positions.append(PositionLot("lot_s047", "0xcond_rally_hwm", "Yes", "BUY", 0.20, 1000.0, 200.0, 7.20, "FILLED", "u_s047"))
    init_s047.open_margin_usd = 200.0
    init_s047.free_cash_usd = 9800.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S047_PARABOLIC_HWM_RATCHET",
            title="Parabolic Rally Realized HWM Ratchet (0.20 -> 0.80)",
            tier="Tier 1: Order Book",
            description="Verifies High-Water Mark ratchets monotonically on realized 4x gain",
            initial_state=init_s047,
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_rally_hwm", "Yes", 0.80),
            events=[create_event("evt_s047", "0xcond_rally_hwm", "SELL", 0.80, 200.0)],
        )
    )
    # S048: Step-wise flash crash (0.90 -> 0.60 -> 0.30 -> 0.05)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S048_STEPWISE_FLASH_CRASH",
            title="Step-Wise 4-Stage Flash Crash (0.90 -> 0.60 -> 0.30 -> 0.05)",
            tier="Tier 1: Order Book",
            description="Tests multi-step price collapse with incremental buy fills",
            initial_state=create_state("u_s048", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_step_crash", "Yes", 0.50),
            events=[
                create_event("evt_s048_1", "0xcond_step_crash", "BUY", 0.90, 50.0, block_num=4200, log_idx=0),
                create_event("evt_s048_2", "0xcond_step_crash", "BUY", 0.60, 50.0, block_num=4201, log_idx=1),
                create_event("evt_s048_3", "0xcond_step_crash", "BUY", 0.30, 50.0, block_num=4202, log_idx=2),
                create_event("evt_s048_4", "0xcond_step_crash", "BUY", 0.05, 50.0, block_num=4203, log_idx=3),
            ],
        )
    )
    # S049: Step-wise parabolic rally (0.10 -> 0.40 -> 0.70 -> 0.95)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S049_STEPWISE_PARABOLIC_RALLY",
            title="Step-Wise 4-Stage Parabolic Rally (0.10 -> 0.40 -> 0.70 -> 0.95)",
            tier="Tier 1: Order Book",
            description="Tests multi-step price rally with incremental buy fills",
            initial_state=create_state("u_s049", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_step_rally", "Yes", 0.50),
            events=[
                create_event("evt_s049_1", "0xcond_step_rally", "BUY", 0.10, 50.0, block_num=4300, log_idx=0),
                create_event("evt_s049_2", "0xcond_step_rally", "BUY", 0.40, 50.0, block_num=4301, log_idx=1),
                create_event("evt_s049_3", "0xcond_step_rally", "BUY", 0.70, 50.0, block_num=4302, log_idx=2),
                create_event("evt_s049_4", "0xcond_step_rally", "BUY", 0.95, 50.0, block_num=4303, log_idx=3),
            ],
        )
    )
    # S050: Flash crash to near-zero with non-zero residual spread
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S050_CRASH_RESIDUAL_SPREAD",
            title="Flash Crash to Floor with 0.5 Cent Residual Spread",
            tier="Tier 1: Order Book",
            description="Validates pricing at Bid 0.010 / Ask 0.015 post-crash",
            initial_state=create_state("u_s050", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_normal_book("0xcond_crash_res", "Yes", 0.0125, spread=0.005),
            events=[create_event("evt_s050", "0xcond_crash_res", "BUY", 0.015, 100.0)],
        )
    )

    # ------------------------------------------------------------------------
    # S051 - S055: Zero-Price & Ceiling Contracts (5 Scenarios)
    # ------------------------------------------------------------------------
    # S051: Zero-price contract $p=0.000 (clamped to 0.001)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S051_ZERO_PRICE_CLAMP",
            title="Zero-Price Contract Exact Zero-Clamp ($p=0.000 -> 0.001)",
            tier="Tier 1: Order Book",
            description="Tests fee calculation and sizing guard against division by zero at p=0.000",
            initial_state=create_state("u_s051", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_zero_price_contract_book("0xcond_p0"),
            events=[create_event("evt_s051", "0xcond_p0", "BUY", 0.000, 50.0)],
        )
    )
    # S052: Ceiling contract $p=1.000 (clamped to 0.999)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S052_CEILING_PRICE_CLAMP",
            title="Ceiling-Price Contract Exact Clamp ($p=1.000 -> 0.999)",
            tier="Tier 1: Order Book",
            description="Tests fee calculation and non-overflow at p=1.000 ceiling",
            initial_state=create_state("u_s052", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_ceiling_price_contract_book("0xcond_p1"),
            events=[create_event("evt_s052", "0xcond_p1", "BUY", 1.000, 100.0)],
        )
    )
    # S053: Sub-cent price boundary $p=0.0005
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S053_SUB_CENT_BOUNDARY",
            title="Sub-Cent Price Boundary Evaluation ($p=0.0005)",
            tier="Tier 1: Order Book",
            description="Tests quadratic fee curve at sub-cent boundary without numerical instability",
            initial_state=create_state("u_s053", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_zero_price_contract_book("0xcond_p0005"),
            events=[create_event("evt_s053", "0xcond_p0005", "BUY", 0.0005, 50.0)],
        )
    )
    # S054: Near-ceiling boundary $p=0.9995
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S054_NEAR_CEILING_BOUNDARY",
            title="Near-Ceiling Price Boundary Evaluation ($p=0.9995)",
            tier="Tier 1: Order Book",
            description="Tests quadratic fee curve at 99.95% boundary without overflow",
            initial_state=create_state("u_s054", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_ceiling_price_contract_book("0xcond_p9995"),
            events=[create_event("evt_s054", "0xcond_p9995", "BUY", 0.9995, 100.0)],
        )
    )
    # S055: Exact zero-price contract order execution and fee non-negativity
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S055_ZERO_PRICE_FEE_NON_NEGATIVITY",
            title="Zero-Price Fee Non-Negativity & Margin Safety",
            tier="Tier 1: Order Book",
            description="Validates all 10 invariants on zero-price order execution",
            initial_state=create_state("u_s055", 10000.0),
            order_book_factory=lambda: MockMarketFactory.create_zero_price_contract_book("0xcond_p0_inv"),
            events=[create_event("evt_s055", "0xcond_p0_inv", "BUY", 0.000, 100.0)],
        )
    )

    return scenarios


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

ALL_TIER_1_SCENARIOS = build_orderbook_extremes_scenarios()


def test_tier_1_scenario_count():
    """Verify exactly 55 scenarios are defined in Tier 1 suite."""
    assert len(ALL_TIER_1_SCENARIOS) == 55, f"Expected 55 scenarios, got {len(ALL_TIER_1_SCENARIOS)}"


@pytest.mark.parametrize("scenario", ALL_TIER_1_SCENARIOS, ids=lambda s: s.scenario_id)
def test_individual_orderbook_extreme_scenario(runner: ScenarioRunner, scenario: ScenarioDefinition):
    """Executes each of the 55 Order Book Extreme scenarios individually against InvariantMonitor."""
    result = runner.run_scenario(scenario)
    assert result.passed is True, (
        f"Scenario {scenario.scenario_id} failed with {len(result.violations)} violations: "
        f"{[v.message for v in result.violations]}"
    )
    assert len(result.violations) == 0
    assert all(s.status == "PASS" for s in result.steps)


def test_tier_1_orderbook_extremes_aggregate_matrix(runner: ScenarioRunner):
    """Executes all 55 Order Book Extreme scenarios in batch matrix and produces summary."""
    report: ScenarioReport = runner.run_matrix(ALL_TIER_1_SCENARIOS)
    assert report.total_scenarios == 55
    assert report.passed_scenarios == 55
    assert report.failed_scenarios == 0
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0
