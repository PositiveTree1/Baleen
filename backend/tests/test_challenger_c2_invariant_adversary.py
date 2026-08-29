"""
Adversarial Invariant & 220-Scenario Challenger Suite (Challenger 2).

Probes the 4 core Baleen invariants:
  1. 10-Wallet Sleeve Isolation & Zero Capital Starvation
  2. Cash Invariance & MTM Isolation (No negative cash, no phantom cash inflation)
  3. 2026 Quadratic Polymarket Fee Invariance across all 6 categories
  4. Zero-Division Safety on single-trade / zero-volume / corrupted orderbooks / Monte Carlo edge cases
"""

import copy
import decimal
import math
import random
import pytest

from app.sizing.sleeve_manager import SleeveManager, SleeveAllocation, SleeveSizingResult
from app.services.polymarket_fees import (
    calculate_polymarket_fee,
    calculate_fee_aware_ev_gate,
    classify_market_category,
)
from app.sizing.fill_simulator import simulate_fill, FillResult
from app.sizing.dynamic_sizer import size_trade, SizingResult
from tests.scenarios.invariant_monitor import (
    InvariantCheckType,
    InvariantMonitor,
    PortfolioState,
    PositionLot,
    TradeExecution,
)
from tests.scenarios.runner import (
    ScenarioDefinition,
    ScenarioRunner,
)
from tests.scenarios.mock_market_factory import MockMarketFactory, SyntheticEvent


# ============================================================================
# 1. SLEEVE ISOLATION & ZERO CAPITAL STARVATION ADVERSARIAL STRESS
# ============================================================================

class TestSleeveIsolationAdversarial:
    """Stress tests 10-wallet sleeve isolation and anti-starvation mechanics."""

    def test_9_exhausted_sleeves_do_not_starve_10th_wallet(self):
        """When 9 out of 10 wallets exhaust 100% of their sleeve budget, the 10th wallet still executes 100%."""
        total_bankroll = 10000.0
        active_roster = 10
        sleeve_budget = SleeveManager.calculate_sleeve_budget(total_bankroll, active_roster)
        assert sleeve_budget == 1000.0

        # Simulate 9 wallets having exhausted their $1,000 sleeves
        for i in range(9):
            res_exhausted = SleeveManager.size_sleeve_trade(
                wallet_address=f"0xExhausted_{i}",
                whale_trade_size_usd=500.0,
                sleeve_budget_usd=sleeve_budget,
                open_notional_usd=1000.0,  # 100% exhausted
                trailing_sizes=[100.0, 500.0],
            )
            assert res_exhausted.actual_size_usd == 0.0
            assert res_exhausted.status == "SKIPPED_SLEEVE_EXHAUSTED"

        # 10th wallet with $0 open notional gets full conviction size
        res_fresh = SleeveManager.size_sleeve_trade(
            wallet_address="0xFresh_10",
            whale_trade_size_usd=1000.0,
            sleeve_budget_usd=sleeve_budget,
            open_notional_usd=0.0,
            trailing_sizes=[100.0, 200.0, 500.0, 1000.0],
        )
        assert res_fresh.actual_size_usd == 1000.0
        assert res_fresh.status == "SUCCESS"
        assert res_fresh.is_clipped is False
        assert res_fresh.capture_rate_pct == 100.0

    def test_sleeve_budget_edge_cases(self):
        """Probes boundary values for bankroll and roster sizing."""
        assert SleeveManager.calculate_sleeve_budget(0.0, 10) == 0.0
        assert SleeveManager.calculate_sleeve_budget(-500.0, 10) == 0.0
        assert SleeveManager.calculate_sleeve_budget(10000.0, 0) == 0.0
        assert SleeveManager.calculate_sleeve_budget(10000.0, -5) == 0.0
        assert SleeveManager.calculate_sleeve_budget(1.0, 10) == 0.10
        assert SleeveManager.calculate_sleeve_budget(1000000.0, 1) == 1000000.0

    def test_conviction_percentile_adversarial_inputs(self):
        """Probes empty, single-element, all-zero, negative, and extreme trailing sizes."""
        # Empty trailing sizes -> neutral 0.50
        assert SleeveManager.calculate_conviction_percentile(100.0, []) == 0.50

        # All zeros or negative -> fallback 0.50
        assert SleeveManager.calculate_conviction_percentile(100.0, [0.0, 0.0, -10.0]) == 0.50

        # Single trade history -> 1.0 (since 100 <= 100)
        assert SleeveManager.calculate_conviction_percentile(100.0, [100.0]) == 1.0
        assert SleeveManager.calculate_conviction_percentile(50.0, [100.0]) == 0.05  # clamped min

        # Zero or negative trade size
        assert SleeveManager.calculate_conviction_percentile(0.0, [10.0, 20.0]) == 0.05
        assert SleeveManager.calculate_conviction_percentile(-50.0, [10.0, 20.0]) == 0.05

    def test_copy_pnl_ema_clamping_and_drift(self):
        """EMA adjustments strictly honor 0.30x floor and 1.50x cap regardless of runaway PnL."""
        base_budget = 1000.0

        # Runaway profit (+$1,000,000 PnL) -> capped at 1.50x ($1,500)
        assert SleeveManager.calculate_adjusted_sleeve_budget(base_budget, 1_000_000.0) == 1500.0

        # Runaway loss (-$1,000,000 PnL) -> floored at 0.30x ($300, NEVER negative or zero)
        assert SleeveManager.calculate_adjusted_sleeve_budget(base_budget, -1_000_000.0) == 300.0

        # Base budget 0
        assert SleeveManager.calculate_adjusted_sleeve_budget(0.0, 500.0) == 0.0


# ============================================================================
# 2. CASH INVARIANCE & MTM ISOLATION ADVERSARIAL STRESS
# ============================================================================

class TestCashInvarianceAndMTMAdversarial:
    """Stress tests cash invariance, phantom cash prevention, and margin equation."""

    def test_massive_unrealized_gains_do_not_inflate_settled_or_free_cash(self):
        """
        Buying $500 of a $0.01 contract (50,000 shares) that spikes to $0.99 ($49,500 unrealized gain)
        must NOT inflate settled cash or free cash until sold.
        """
        monitor = InvariantMonitor(strict_mode=True)
        initial_cash = 10000.0

        # Step 1: Initial State
        state_0 = PortfolioState(
            user_id="user_whale",
            settled_cash_usd=initial_cash,
            free_cash_usd=initial_cash,
            open_margin_usd=0.0,
            high_water_mark_usd=initial_cash,
            equity_usd=initial_cash,
        )
        assert monitor.validate_transition(None, state_0).is_valid

        # Step 2: Open $500 position in Crypto market at $0.01
        notional_bought = 500.0
        open_lot = PositionLot(
            lot_id="lot_crypto_1",
            condition_id="0xcrypto_moon",
            outcome="Yes",
            side="BUY",
            price=0.01,
            shares=50000.0,
            notional_usd=notional_bought,
            fee_usd=3.56,
            status="FILLED",
            user_id="user_whale",
        )
        state_1 = PortfolioState(
            user_id="user_whale",
            settled_cash_usd=initial_cash,  # Settled cash unchanged on open (collateralized in open margin)
            free_cash_usd=initial_cash - notional_bought,  # $9,500
            open_margin_usd=notional_bought,  # $500
            high_water_mark_usd=initial_cash,
            open_positions=[open_lot],
            total_unrealized_pnl_usd=0.0,
            equity_usd=initial_cash,
        )
        tx_buy = TradeExecution(
            trade_id="tx_1",
            condition_id="0xcrypto_moon",
            outcome="Yes",
            side="BUY",
            price=0.01,
            shares=50000.0,
            notional_usd=notional_bought,
            fee_usd=3.56,
            user_id="user_whale",
            market_category="Crypto",
        )
        assert monitor.validate_transition(state_0, state_1, tx_buy).is_valid

        # Step 3: Pure MTM Valuation Cycle — price surges to $0.99
        # Unrealized PnL = 50000 * 0.99 - 500 = $49,000.00
        unrealized_pnl = 49000.0
        state_2 = PortfolioState(
            user_id="user_whale",
            settled_cash_usd=initial_cash,  # MUST REMAIN $10,000.00 (NO PHANTOM CASH)
            free_cash_usd=initial_cash - notional_bought,  # MUST REMAIN $9,500.00
            open_margin_usd=notional_bought,  # $500.00
            high_water_mark_usd=initial_cash + unrealized_pnl,  # $59,000.00
            open_positions=[open_lot],
            total_unrealized_pnl_usd=unrealized_pnl,
            equity_usd=initial_cash + unrealized_pnl,  # $59,000.00
        )
        # No trade executed in this step
        res_mtm = monitor.validate_transition(state_1, state_2, execution=None)
        assert res_mtm.is_valid, f"MTM cycle failed invariants: {res_mtm.violations}"

        # Step 4: Adversarial Test — If a bug mistakenly inflated settled cash to $59,000 during MTM:
        state_corrupt = copy.deepcopy(state_2)
        state_corrupt.settled_cash_usd = 59000.0  # LEAK!
        res_corrupt = monitor.validate_transition(state_1, state_corrupt, execution=None)
        assert not res_corrupt.is_valid
        assert any(v.check_type == InvariantCheckType.MTM_CASH_ISOLATION for v in res_corrupt.violations)

    def test_fifo_partial_lot_split_precision_conservation(self):
        """Probes FIFO partial splits with prime numbers and sub-cent remainders."""
        monitor = InvariantMonitor(strict_mode=True)
        orig_lot = PositionLot(
            lot_id="lot_orig",
            condition_id="0xcond_prime",
            outcome="Yes",
            side="BUY",
            price=0.3333,
            shares=3000.3000,
            notional_usd=1000.00,
            fee_usd=16.00,
            status="FILLED",
        )

        # Split into 3 uneven slices: $333.33, $333.33, $333.34
        s1 = PositionLot("s1", "0xcond_prime", "Yes", "BUY", 0.3333, 1000.0900, 333.33, 5.3333, "CLOSED")
        s2 = PositionLot("s2", "0xcond_prime", "Yes", "BUY", 0.3333, 1000.0900, 333.33, 5.3333, "CLOSED")
        s3 = PositionLot("s3", "0xcond_prime", "Yes", "BUY", 0.3333, 1000.1200, 333.34, 5.3334, "FILLED")

        violations = monitor.check_fifo_lot_split_conservation(orig_lot, [s1, s2, s3])
        assert len(violations) == 0, f"Split conservation failed on prime split: {violations}"


# ============================================================================
# 3. 2026 QUADRATIC POLYMARKET FEE INVARIANCE ADVERSARIAL SWEEP
# ============================================================================

class TestPolymarketFeeInvarianceAdversarial:
    """Stress tests quadratic taker fees across all categories, boundary prices, and rounding rules."""

    @pytest.mark.parametrize(
        "title,expected_cat,expected_theta",
        [
            ("Bitcoin Up or Down 15m", "Crypto", 0.072),
            ("Ethereum Price Above $4000", "Crypto", 0.072),
            ("Fed Interest Rate Decision September", "Economics / Finance", 0.060),
            ("US CPI Inflation YoY", "Economics / Finance", 0.060),
            ("Apple WWDC Keynote Announcement", "Culture, Weather & Tech", 0.050),
            ("OpenAI GPT-5 Release Date", "Culture, Weather & Tech", 0.050),
            ("Presidential Election Winner 2028", "Politics", 0.040),
            ("Senate Majority Control", "Politics", 0.040),
            ("Real Madrid vs Manchester City Champions League", "Sports", 0.030),
            ("Novak Djokovic ATP Finals Winner", "Sports", 0.030),
            ("Russia Ukraine Ceasefire Agreement", "Geopolitics", 0.000),
            ("Taiwan Strait Sanctions Resolution", "Geopolitics", 0.000),
            ("Unknown Market Question", "General", 0.050),
        ],
    )
    def test_category_classification_thetas(self, title, expected_cat, expected_theta):
        cat, theta = classify_market_category(title)
        assert cat == expected_cat
        assert theta == expected_theta

    def test_bankers_rounding_half_to_even_rigorous_cents(self):
        """
        Banker's Rounding (ROUND_HALF_EVEN) requires:
          - $0.025 -> $0.02 (round down to even 2)
          - $0.035 -> $0.04 (round up to even 4)
          - $0.045 -> $0.04 (round down to even 4)
          - $0.055 -> $0.06 (round up to even 6)
        """
        cases = [
            ("0.025", 0.02),
            ("0.035", 0.04),
            ("0.045", 0.04),
            ("0.055", 0.06),
            ("1.125", 1.12),
            ("1.135", 1.14),
        ]
        for val_str, expected in cases:
            d = decimal.Decimal(val_str).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_EVEN)
            assert float(d) == expected

    def test_fee_bounds_monte_carlo_sweep(self):
        """Runs 500 random notionals and prices across all categories to verify fee bounds."""
        categories = [
            ("Will Bitcoin hit 100k?", 0.072),
            ("Fed Rate Cut in June", 0.060),
            ("Apple AI Release", 0.050),
            ("Presidential Election 2028", 0.040),
            ("Champions League Final Real Madrid vs Arsenal", 0.030),
            ("Peace Treaty Ceasefire in Middle East", 0.000),
        ]
        monitor = InvariantMonitor(strict_mode=True)

        for _ in range(500):
            notional = round(random.uniform(1.0, 50000.0), 2)
            price = round(random.uniform(0.001, 0.999), 4)
            market_title, theta = random.choice(categories)

            res = calculate_polymarket_fee(notional, price, market_title)
            fee = res["fee_usd"]

            # Mathematical invariant: Fee <= Theta * Notional * (1 - p) + $0.01 tolerance
            max_expected_fee = round(theta * notional * (1.0 - price) + 0.015, 2)
            assert fee >= 0.0, f"Negative fee {fee} for notional {notional}"
            assert fee <= max_expected_fee, f"Fee {fee} exceeded max {max_expected_fee}"

            # Audit against monitor
            tx = TradeExecution(
                trade_id="tx_sweep",
                condition_id="0xcond",
                outcome="Yes",
                side="BUY",
                price=price,
                shares=notional / price,
                notional_usd=notional,
                fee_usd=fee,
                market_category=res["category"],
            )
            violations = monitor.check_fee_bounds(tx, max_theta=0.072)
            assert len(violations) == 0, f"Fee bounds violated: {violations}"

    def test_ev_net_gate_boundary_precision(self):
        """Verifies EV_net gate threshold: Expected Edge > 2.5 * [Theta * (1 - p)]."""
        # Crypto market at p = 0.50: Theta = 0.072 -> fee_rate = 0.072 * 0.50 = 0.036 (3.6%)
        # Min required edge = 2.5 * 0.036 = 0.090 (9.0%)
        pass_gate, fee_rate, min_edge = calculate_fee_aware_ev_gate(
            price=0.50, market_title="Bitcoin 15m", expected_edge=0.091
        )
        assert pass_gate is True
        assert round(min_edge, 4) == 0.0900

        fail_gate, _, _ = calculate_fee_aware_ev_gate(
            price=0.50, market_title="Bitcoin 15m", expected_edge=0.089
        )
        assert fail_gate is False


# ============================================================================
# 4. ZERO-DIVISION SAFETY & CORRUPTED ORDERBOOKS ADVERSARIAL STRESS
# ============================================================================

class TestZeroDivisionAndCorruptedOrderbooksAdversarial:
    """Stress tests zero-division guards and resilience to corrupt/degenerate inputs."""

    def test_fill_simulator_empty_and_zero_price_books(self):
        """Simulates fills against empty books and zero/negative priced levels."""
        # 1. Empty asks dictionary
        book_empty = {"bids": [], "asks": []}
        res1 = simulate_fill(order_value_usd=100.0, order_book=book_empty, side="BUY")
        assert res1.total_filled == 0.0
        assert res1.avg_price == 0.0

        # 2. Book with only zero and negative price levels
        book_corrupt = {
            "asks": [
                {"price": 0.0, "size": 100.0},
                {"price": -0.50, "size": 50.0},
            ]
        }
        res2 = simulate_fill(order_value_usd=100.0, order_book=book_corrupt, side="BUY")
        assert res2.total_filled == 0.0
        assert res2.avg_price == 0.0

        # 3. Book with leading zero price followed by valid level
        book_mixed = {
            "asks": [
                {"price": 0.0, "size": 100.0},
                {"price": 0.50, "size": 100.0},
            ]
        }
        res3 = simulate_fill(order_value_usd=25.0, order_book=book_mixed, side="BUY")
        assert res3.total_filled == 25.0
        assert res3.avg_price == 0.50

    def test_dynamic_sizer_degenerate_portfolios(self):
        """Verifies size_trade handles 0 balance, negative balance, 0 active wallets gracefully."""
        # 0 active wallets
        res1 = size_trade(
            user_balance=10000.0,
            risk_profile="balanced",
            n_active=0,
            whale_trade_value=1000.0,
            whale_portfolio_value=50000.0,
        )
        assert res1.value == 0.0
        assert res1.status == "SKIPPED_NO_ACTIVE_WALLETS"

        # 0 user balance
        res2 = size_trade(
            user_balance=0.0,
            risk_profile="balanced",
            n_active=10,
            whale_trade_value=1000.0,
            whale_portfolio_value=50000.0,
        )
        assert res2.value == 0.0
        assert res2.status == "SKIPPED_BELOW_MINIMUM"

        # 0 whale portfolio value
        res3 = size_trade(
            user_balance=10000.0,
            risk_profile="balanced",
            n_active=10,
            whale_trade_value=1000.0,
            whale_portfolio_value=0.0,
        )
        assert res3.value == 0.0
        assert res3.status == "SKIPPED_INVALID_PORTFOLIO"

    def test_numerical_safety_nan_and_inf_detection(self):
        """Verifies that InvariantMonitor detects and flags NaNs and Infs immediately."""
        monitor = InvariantMonitor(strict_mode=True)

        state_nan = PortfolioState(
            user_id="u_nan",
            settled_cash_usd=float("nan"),
            free_cash_usd=1000.0,
            open_margin_usd=0.0,
            high_water_mark_usd=1000.0,
            equity_usd=1000.0,
        )
        v_nan = monitor.check_numerical_safety(state_nan)
        assert len(v_nan) > 0
        assert any(v.check_type == InvariantCheckType.NUMERICAL_IEEE_SAFETY for v in v_nan)

        state_inf = PortfolioState(
            user_id="u_inf",
            settled_cash_usd=1000.0,
            free_cash_usd=float("inf"),
            open_margin_usd=0.0,
            high_water_mark_usd=1000.0,
            equity_usd=1000.0,
        )
        v_inf = monitor.check_numerical_safety(state_inf)
        assert len(v_inf) > 0
        assert any(v.check_type == InvariantCheckType.NUMERICAL_IEEE_SAFETY for v in v_inf)
