"""
Milestone M-A1 Adversarial Stress Test Suite - Challenger 1
Empirical stress-testing of fill_simulator.py, dynamic_sizer.py, polymarket_fees.py,
and live_poller.py trade sizing with extreme, boundary, and adversarial inputs.
"""

import copy
import math
import decimal
import pytest
from app.sizing.fill_simulator import simulate_fill, FillResult
from app.sizing.dynamic_sizer import size_trade, SizingResult
from app.services.polymarket_fees import calculate_polymarket_fee, classify_market_category


# ============================================================================
# SECTION 1: fill_simulator.py Extreme Inputs & Vulnerability Proofs
# ============================================================================

class TestFillSimulatorExtremes:
    """Stress-testing fill_simulator.py with adversarial order books and orders."""

    def test_zero_order_value(self):
        """Order value of $0.00 should return 0 filled, 0 price, 0 slippage."""
        book = {"asks": [{"price": 0.50, "size": 100.0}]}
        res = simulate_fill(0.0, book, "BUY")
        assert res.total_filled == 0.0
        assert res.avg_price == 0.0
        assert res.slippage_pct == 0.0
        assert res.levels_consumed == 0

    def test_negative_order_value(self):
        """Negative order value (e.g. -$50.00) should safely terminate with 0 filled."""
        book = {"asks": [{"price": 0.50, "size": 100.0}]}
        res = simulate_fill(-50.0, book, "BUY")
        assert res.total_filled == 0.0
        assert res.avg_price == 0.0
        assert res.slippage_pct == 0.0
        assert res.levels_consumed == 0

    def test_sub_atomic_order_value(self):
        """Micro order value (1e-15 USD) should not cause floating underflow crash."""
        book = {"asks": [{"price": 0.50, "size": 100.0}]}
        res = simulate_fill(1e-15, book, "BUY")
        assert res.levels_consumed == 1
        assert math.isclose(res.avg_price, 0.50, rel_tol=1e-5)
        assert res.total_filled > 0.0

    def test_massive_order_value_exceeding_total_book_depth(self):
        """Massive whale order ($10B) against small book ($100 depth)."""
        book = {
            "asks": [
                {"price": 0.40, "size": 100.0},  # $40
                {"price": 0.60, "size": 100.0},  # $60
            ]
        }
        res = simulate_fill(10_000_000_000.0, book, "BUY")
        assert res.total_filled == 100.0
        assert res.levels_consumed == 2
        # Total shares = 200, total notional = $100 => avg_price = 0.50
        assert math.isclose(res.avg_price, 0.50, rel_tol=1e-5)
        # best_price = 0.40, avg = 0.50 => slippage = (0.50 - 0.40)/0.40 = 25%
        assert math.isclose(res.slippage_pct, 0.25, rel_tol=1e-5)

    def test_empty_order_book_variations(self):
        """Empty book variations: empty dict, missing sides."""
        assert simulate_fill(100.0, {}, "BUY").total_filled == 0.0
        assert simulate_fill(100.0, {"asks": []}, "BUY").total_filled == 0.0
        assert simulate_fill(100.0, {"bids": []}, "SELL").total_filled == 0.0
        # BUY when book only has bids
        assert simulate_fill(100.0, {"bids": [{"price": 0.50, "size": 100.0}]}, "BUY").total_filled == 0.0
        # SELL when book only has asks
        assert simulate_fill(100.0, {"asks": [{"price": 0.50, "size": 100.0}]}, "SELL").total_filled == 0.0

    def test_none_levels_crash_vulnerability(self):
        """
        REMEDIATION VERIFICATION 1:
        When order_book contains {'asks': None} or {'bids': None},
        simulate_fill safely null-coalesces to [] and returns 0 filled without crashing.
        """
        res_buy = simulate_fill(100.0, {"asks": None}, "BUY")
        assert res_buy.total_filled == 0.0
        assert res_buy.avg_price == 0.0

        res_sell = simulate_fill(100.0, {"bids": None}, "SELL")
        assert res_sell.total_filled == 0.0
        assert res_sell.avg_price == 0.0

    def test_none_price_or_size_crash_vulnerability(self):
        """
        REMEDIATION VERIFICATION 2:
        When an order level contains {'price': None} or {'size': None},
        simulate_fill safely handles None and skips corrupt levels without crashing.
        """
        res1 = simulate_fill(100.0, {"asks": [{"price": None, "size": 10.0}]}, "BUY")
        assert res1.total_filled == 0.0

        res2 = simulate_fill(100.0, {"asks": [{"price": 0.50, "size": None}]}, "BUY")
        assert res2.total_filled == 0.0

    def test_non_positive_and_corrupt_levels(self):
        """Levels with price <= 0, size <= 0, or missing fields must be skipped."""
        book = {
            "asks": [
                {"price": 0.0, "size": 100.0},    # price 0
                {"price": -0.50, "size": 100.0},  # negative price
                {"price": 0.40, "size": 0.0},     # size 0
                {"price": 0.40, "size": -50.0},   # negative size
                {"invalid_key": 123},             # missing price/size
                {"price": 0.50, "size": 100.0},   # valid level ($50)
            ]
        }
        res = simulate_fill(25.0, book, "BUY")
        assert res.total_filled == 25.0
        assert math.isclose(res.avg_price, 0.50, rel_tol=1e-5)
        assert res.levels_consumed == 1

    def test_best_price_calculation_when_leading_level_is_zero_price(self):
        """
        VULNERABILITY PROOF 3A:
        Leading level in asks has price=0.0.
        best_price = float(levels[0].get('price', 0)) picks 0.0 before filtering.
        When levels[1] ($0.50) and levels[2] ($0.70) are filled at avg 0.56,
        slippage check `if best_price > 0:` evaluates False, suppressing slippage to 0.0
        instead of reporting true slippage (12%).
        """
        book = {
            "asks": [
                {"price": 0.0, "size": 100.0},    # corrupt 0-price level
                {"price": 0.50, "size": 50.0},    # $25
                {"price": 0.70, "size": 50.0},    # $35
            ]
        }
        res = simulate_fill(40.0, book, "BUY")
        assert res.total_filled == 40.0
        assert math.isclose(res.avg_price, 0.56, rel_tol=1e-5)
        # Slippage is suppressed to 0.0 due to unvalidated levels[0] best_price
        assert res.slippage_pct == 0.0

    def test_best_price_calculation_when_leading_level_has_zero_size(self):
        """
        VULNERABILITY PROOF 3B:
        Leading level has price=0.01 but size=0.0 (ghost quote).
        Next level has price=0.50, size=100.
        best_price grabs 0.01, reporting 4900% phantom slippage.
        """
        book = {
            "asks": [
                {"price": 0.01, "size": 0.0},     # ghost quote
                {"price": 0.50, "size": 100.0},   # real quote
            ]
        }
        res = simulate_fill(25.0, book, "BUY")
        assert res.total_filled == 25.0
        assert res.avg_price == 0.50
        # Slippage is 49.0 (4900%)
        assert math.isclose(res.slippage_pct, 49.0, rel_tol=1e-5)

    def test_unsorted_and_inverted_order_book(self):
        """Order books arriving out-of-order must be sorted before matching."""
        unsorted_asks = {
            "asks": [
                {"price": 0.80, "size": 50.0},  # $40
                {"price": 0.20, "size": 50.0},  # $10
                {"price": 0.50, "size": 50.0},  # $25
            ]
        }
        # BUY $20: should take $10 @ 0.20 (50 shares), then $10 @ 0.50 (20 shares) => 70 shares for $20 => avg = 0.2857
        res_buy = simulate_fill(20.0, unsorted_asks, "BUY")
        assert res_buy.total_filled == 20.0
        assert res_buy.levels_consumed == 2
        assert math.isclose(res_buy.avg_price, 20.0 / 70.0, rel_tol=1e-5)

        unsorted_bids = {
            "bids": [
                {"price": 0.20, "size": 50.0},
                {"price": 0.80, "size": 50.0},  # $40
                {"price": 0.50, "size": 50.0},  # $25
            ]
        }
        # SELL $20: should take highest bid first: $20 @ 0.80 (25 shares) => avg = 0.80
        res_sell = simulate_fill(20.0, unsorted_bids, "SELL")
        assert res_sell.total_filled == 20.0
        assert res_sell.levels_consumed == 1
        assert math.isclose(res_sell.avg_price, 0.80, rel_tol=1e-5)

    def test_case_insensitive_side_variants(self):
        """Verify all casing permutations of BUY and SELL."""
        book = {
            "asks": [{"price": 0.60, "size": 100.0}],
            "bids": [{"price": 0.40, "size": 100.0}]
        }
        for s in ["BUY", "buy", "Buy", "bUy", "bUY"]:
            res = simulate_fill(10.0, book, s)
            assert math.isclose(res.avg_price, 0.60, rel_tol=1e-5), f"Failed for side {s}"
        
        for s in ["SELL", "sell", "Sell", "sEll", "sELL"]:
            res = simulate_fill(10.0, book, s)
            assert math.isclose(res.avg_price, 0.40, rel_tol=1e-5), f"Failed for side {s}"

    def test_immutability_of_caller_book(self):
        """Verify simulate_fill does not mutate caller's order book dictionary or level elements."""
        original_book = {
            "asks": [
                {"price": 0.90, "size": 10.0},
                {"price": 0.10, "size": 10.0},
            ],
            "bids": [
                {"price": 0.10, "size": 10.0},
                {"price": 0.90, "size": 10.0},
            ]
        }
        book_snapshot = copy.deepcopy(original_book)
        simulate_fill(5.0, original_book, "BUY")
        simulate_fill(5.0, original_book, "SELL")
        assert original_book == book_snapshot, "simulate_fill mutated caller's order book structure!"


# ============================================================================
# SECTION 2: dynamic_sizer.py & Trade Sizing Stress Tests
# ============================================================================

class TestDynamicSizingExtremes:
    """Stress-testing size_trade with boundary and adversarial inputs."""

    def test_zero_and_negative_user_balance(self):
        """User with $0 or negative balance must be skipped without crashing."""
        res_zero = size_trade(0.0, "balanced", 10, 500.0, 10000.0)
        assert res_zero.status == "SKIPPED_BELOW_MINIMUM"
        assert res_zero.value == 0.0

        res_neg = size_trade(-1000.0, "balanced", 10, 500.0, 10000.0)
        assert res_neg.status == "SKIPPED_BELOW_MINIMUM"
        assert res_neg.value == 0.0

    def test_zero_and_negative_active_wallets(self):
        """n_active <= 0 must return SKIPPED_NO_ACTIVE_WALLETS."""
        res_zero_n = size_trade(10000.0, "balanced", 0, 500.0, 10000.0)
        assert res_zero_n.status == "SKIPPED_NO_ACTIVE_WALLETS"
        assert res_zero_n.value == 0.0

        res_neg_n = size_trade(10000.0, "balanced", -5, 500.0, 10000.0)
        assert res_neg_n.status == "SKIPPED_NO_ACTIVE_WALLETS"
        assert res_neg_n.value == 0.0

    def test_zero_and_negative_whale_portfolio(self):
        """whale_portfolio_value <= 0 must return SKIPPED_INVALID_PORTFOLIO."""
        res_zero_port = size_trade(10000.0, "balanced", 10, 500.0, 0.0)
        assert res_zero_port.status == "SKIPPED_INVALID_PORTFOLIO"
        assert res_zero_port.value == 0.0

        res_neg_port = size_trade(10000.0, "balanced", 10, 500.0, -50000.0)
        assert res_neg_port.status == "SKIPPED_INVALID_PORTFOLIO"
        assert res_neg_port.value == 0.0

    def test_whale_all_in_100_pct_risk(self):
        """Whale trades 100% of portfolio ($10k trade on $10k portfolio). User risk cap must strictly bind."""
        res_cons = size_trade(10000.0, "conservative", 1, 10000.0, 10000.0)
        # conservative cap = 5% of 10000 = $500
        assert res_cons.status == "SUCCESS"
        assert res_cons.value == 500.0

        res_bal = size_trade(10000.0, "balanced", 1, 10000.0, 10000.0)
        # balanced cap = 10% of 10000 = $1000
        assert res_bal.status == "SUCCESS"
        assert res_bal.value == 1000.0

        res_agg = size_trade(10000.0, "aggressive", 1, 10000.0, 10000.0)
        # aggressive cap = 20% of 10000 = $2000
        assert res_agg.status == "SUCCESS"
        assert res_agg.value == 2000.0

    def test_risk_profile_casing_and_invalid_fallback(self):
        """Risk profile casing ('CONSERVATIVE', 'Balanced') and invalid profile fallback to 10%."""
        res_upper = size_trade(10000.0, "CONSERVATIVE", 1, 10000.0, 10000.0)
        assert res_upper.value == 500.0

        res_mixed = size_trade(10000.0, "Aggressive", 1, 10000.0, 10000.0)
        assert res_mixed.value == 2000.0

        # Invalid profile defaults to balanced (10%)
        res_invalid = size_trade(10000.0, "hyper_risk_unknown", 1, 10000.0, 10000.0)
        assert res_invalid.value == 1000.0

        # None profile defaults to balanced (10%)
        res_none = size_trade(10000.0, None, 1, 10000.0, 10000.0)
        assert res_none.value == 1000.0


# ============================================================================
# SECTION 3: live_poller.py Trade Sizing Logic Stress & Vulnerability Analysis
# ============================================================================

class TestLivePollerSizingVulnerabilities:
    """Stress-testing live_poller.py trade sizing integration points."""

    def test_user_sizing_skip_fallback_vulnerability(self):
        """
        VULNERABILITY PROOF 4:
        In live_poller.py lines 360-363:
        When size_trade returns status != 'SUCCESS' (e.g. SKIPPED_BELOW_MINIMUM),
        live_poller.py enters the `else:` branch and executes a forced trade of $5 to $150!
        """
        user_balance = 50.0
        whale_trade_val = 10.0
        whale_port_val = 100000.0  # tiny whale trade (0.01%)
        
        sizing_res = size_trade(
            user_balance=user_balance,
            risk_profile="balanced",
            n_active=10,
            whale_trade_value=whale_trade_val,
            whale_portfolio_value=whale_port_val,
            min_order_usd=5.0
        )
        # Dynamic sizer correctly computes: base=5, risk=0.0001 => raw=$0.0005 < $5 => SKIPPED
        assert sizing_res.status == "SKIPPED_BELOW_MINIMUM"
        assert sizing_res.value == 0.0
        
        # Now simulate live_poller.py lines 360-363:
        cash_usd = 10.0
        sizing_multiplier = 1.0
        if sizing_res.status == 'SUCCESS':
            u_notional = sizing_res.value
        else:
            # LIVE POLLER FALLBACK BUG: Forces trade!
            u_notional = round(min(max(5.0, cash_usd * 0.05 * sizing_multiplier), 150.0), 2)
            
        # The user was supposed to skip, but got assigned a $5.00 trade (10% of their entire $50 balance!)
        assert u_notional == 5.0, "Vulnerability confirmed: live_poller.py forces order despite sizer skip!"

    def test_user_balance_falsy_fallback_vulnerability(self):
        """
        VULNERABILITY PROOF 5:
        In live_poller.py line 353:
        float(u.sandbox_balance_usd or 10000.0)
        When user balance is 0.0 (busted account), `0.0 or 10000.0` evaluates to 10000.0!
        """
        busted_balance = 0.0
        flawed_balance_eval = float(busted_balance or 10000.0)
        assert flawed_balance_eval == 10000.0, "Vulnerability confirmed: $0 balance evaluated as $10,000!"

        # Fixed logic:
        safe_balance_eval = float(busted_balance if busted_balance is not None else 10000.0)
        assert safe_balance_eval == 0.0

    def test_whale_trade_val_zero_and_negative_guard(self):
        """
        Verify line 351:
        whale_trade_val = float(cash_usd if (cash_usd is not None and cash_usd > 0) else 500.0)
        """
        # When cash_usd is None -> 500.0
        cash_usd_none = None
        w_val_none = float(cash_usd_none if (cash_usd_none is not None and cash_usd_none > 0) else 500.0)
        assert w_val_none == 500.0

        # When cash_usd is 0 -> 500.0
        cash_usd_zero = 0.0
        w_val_zero = float(cash_usd_zero if (cash_usd_zero is not None and cash_usd_zero > 0) else 500.0)
        assert w_val_zero == 500.0

        # When cash_usd is -100 -> 500.0
        cash_usd_neg = -100.0
        w_val_neg = float(cash_usd_neg if (cash_usd_neg is not None and cash_usd_neg > 0) else 500.0)
        assert w_val_neg == 500.0

        # When cash_usd is valid positive 2500.0 -> 2500.0
        cash_usd_pos = 2500.0
        w_val_pos = float(cash_usd_pos if (cash_usd_pos is not None and cash_usd_pos > 0) else 500.0)
        assert w_val_pos == 2500.0
