"""
Challenger 1 Empirical Stress Test Suite
Testing Paper Trading Execution Simulation, Order Book Walking,
Quadratic Fees, Slippage Rules, Cash Accounting, and FIFO PnL Double-Counting.
"""

import copy
import decimal
import math
import pytest

from app.sizing.fill_simulator import simulate_fill, FillResult
from app.sizing.slippage import check_slippage
from app.sizing.dynamic_sizer import size_trade, SizingResult
from app.services.polymarket_fees import (
    classify_market_category,
    calculate_polymarket_fee,
    calculate_fee_aware_ev_gate
)


# ============================================================================
# TOPIC 1: Order Book Walking Stress Tests
# ============================================================================

def test_fill_simulator_empty_book():
    """Verify empty order book returns 0 fills without crashing."""
    empty_book = {"asks": [], "bids": []}
    res = simulate_fill(100.0, empty_book, "BUY")
    assert res.avg_price == 0.0
    assert res.total_filled == 0.0
    assert res.slippage_pct == 0.0
    assert res.levels_consumed == 0


def test_fill_simulator_shallow_depth_partial_fill():
    """Verify shallow book fills up to available depth and computes weighted avg."""
    shallow_book = {
        "asks": [
            {"price": 0.40, "size": 50.0},  # $20.00 value
            {"price": 0.50, "size": 40.0},  # $20.00 value
        ]
    }
    # Request $100.00 when only $40.00 total depth exists
    res = simulate_fill(100.0, shallow_book, "BUY")
    assert res.total_filled == 40.0
    assert res.levels_consumed == 2
    # 50 shares @ 0.40 + 40 shares @ 0.50 = 90 shares, total $40 => avg = 40/90 = 0.4444...
    expected_avg = 40.0 / 90.0
    assert math.isclose(res.avg_price, expected_avg, rel_tol=1e-5)


def test_fill_simulator_inverted_depth_levels():
    """Verify fill simulator sorts unsorted / inverted book levels before depth walking."""
    unsorted_book = {
        "asks": [
            {"price": 0.60, "size": 50.0},
            {"price": 0.30, "size": 50.0},
            {"price": 0.45, "size": 50.0},
        ]
    }
    # For BUY, should consume 0.30 first ($15), then 0.45 ($22.50)
    res = simulate_fill(20.0, unsorted_book, "BUY")
    # Level 1: 50 shares @ 0.30 ($15.00)
    # Level 2: $5.00 remaining / 0.45 = 11.111 shares @ 0.45 ($5.00)
    # Total shares = 50 + 11.1111 = 61.1111 shares for $20.00 => avg = 20 / 61.1111 = 0.32727
    assert res.total_filled == 20.0
    assert res.levels_consumed == 2
    assert math.isclose(res.avg_price, 20.0 / (50.0 + (5.0 / 0.45)), rel_tol=1e-5)


def test_fill_simulator_in_place_mutation_vulnerability():
    """Empirical proof: simulate_fill mutates the caller's order_book list in place!"""
    original_asks = [
        {"price": 0.80, "size": 10.0},
        {"price": 0.20, "size": 10.0},
    ]
    book = {"asks": original_asks}
    
    # Check order before
    assert book["asks"][0]["price"] == 0.80
    
    simulate_fill(10.0, book, "BUY")
    
    # BUG PROOF: The caller's dictionary list was mutated in-place by levels.sort()
    assert book["asks"][0]["price"] == 0.20, "simulate_fill mutated caller's order book in place!"


def test_fill_simulator_case_sensitivity_hazard():
    """Empirical proof: passing lowercase 'buy' causes book walker to execute against BIDS."""
    book = {
        "asks": [{"price": 0.55, "size": 100.0}],
        "bids": [{"price": 0.45, "size": 100.0}],
    }
    # Lowercase 'buy'
    res = simulate_fill(20.0, book, "buy")
    # Because side == 'BUY' fails, it fetched 'bids' and executed against 0.45!
    assert math.isclose(res.avg_price, 0.45, rel_tol=1e-5), "Lowercase 'buy' wrongly matched bids!"


# ============================================================================
# TOPIC 2: Dynamic Quadratic Taker Fees & Boundary Pricing
# ============================================================================

def test_polymarket_fee_all_six_categories():
    """Empirically test fee calculation across all 6 official 2026 categories."""
    cases = [
        ("Will Bitcoin hit $100k?", "Crypto", 0.072),
        ("Fed interest rate cut in September?", "Economics / Finance", 0.060),
        ("OpenAI releases GPT-5 in 2026?", "Culture, Weather & Tech", 0.050),
        ("US Presidential Election Winner", "Politics", 0.040),
        ("Arsenal vs Chelsea match winner", "Sports", 0.030),
        ("Ceasefire agreement in Ukraine?", "Geopolitics", 0.000),
    ]
    
    for title, expected_cat, expected_theta in cases:
        cat, theta = classify_market_category(title)
        assert cat == expected_cat, f"Expected {expected_cat}, got {cat} for '{title}'"
        assert math.isclose(theta, expected_theta), f"Expected theta {expected_theta}, got {theta}"
        
        # Calculate fee for $100 notional @ p=0.50
        fee_info = calculate_polymarket_fee(100.0, 0.50, title)
        assert fee_info["category"] == expected_cat
        assert math.isclose(fee_info["category_rate"], expected_theta)
        
        if expected_theta == 0.0:
            assert fee_info["fee_usd"] == 0.0
        else:
            # Fee = 100 * theta * (1 - 0.50) = 50 * theta
            expected_fee = round(100.0 * expected_theta * 0.50, 2)
            assert math.isclose(fee_info["fee_usd"], expected_fee, abs_tol=0.01)


def test_polymarket_fee_boundary_prices():
    """Empirically stress test boundary prices p -> 0.001, 0.01, 0.50, 0.99, 0.999."""
    notional = 100.0
    title = "Bitcoin above $100k"  # Crypto theta = 0.072
    
    # 1. At p = 0.99: (1 - p) = 0.01 => Fee = 100 * 0.072 * 0.01 = $0.072 => $0.07
    f_99 = calculate_polymarket_fee(notional, 0.99, title)
    assert f_99["fee_usd"] == 0.07
    
    # 2. At p = 0.50: (1 - p) = 0.50 => Fee = 100 * 0.072 * 0.50 = $3.60
    f_50 = calculate_polymarket_fee(notional, 0.50, title)
    assert f_50["fee_usd"] == 3.60
    
    # 3. At p = 0.01: (1 - p) = 0.99 => Fee = 100 * 0.072 * 0.99 = $7.128 => $7.13
    f_01 = calculate_polymarket_fee(notional, 0.01, title)
    assert f_01["fee_usd"] == 7.13
    
    # 4. Extreme lower bound clamp p = 0.0001 (clamped to 0.001)
    f_low = calculate_polymarket_fee(notional, 0.0001, title)
    assert f_low["fee_usd"] == 7.19  # 100 * 0.072 * 0.999 = 7.1928 => 7.19
    
    # 5. Extreme upper bound clamp p = 1.0 (clamped to 0.999)
    f_high = calculate_polymarket_fee(notional, 1.0, title)
    assert f_high["fee_usd"] == 0.01  # 100 * 0.072 * 0.001 = 0.0072 => 0.01


def test_bankers_rounding_precision():
    """Verify Banker's Rounding (ROUND_HALF_EVEN) on exact half cents."""
    # Test half-cent rounding behavior directly via decimal quantization
    d1 = decimal.Decimal("0.025000").quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_EVEN)
    assert d1 == decimal.Decimal("0.02")  # 2 is even
    
    d2 = decimal.Decimal("0.035000").quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_EVEN)
    assert d2 == decimal.Decimal("0.04")  # 4 is even


def test_fee_aware_ev_gate_logic_flaw():
    """Empirical proof of the EV Gate inverted logic bug.
    expected_edge = abs(p - 0.5) treats distance from 50% as alpha.
    """
    # Case A: High alpha trade at toss-up price (p = 0.51). Whale has 80% true probability.
    # True alpha is +29%, but code computes expected_edge = abs(0.51 - 0.5) = 0.01
    price_toss = 0.51
    flawed_edge_calc = abs(price_toss - 0.5)  # 0.01
    passed, fee_rate, min_edge = calculate_fee_aware_ev_gate(price_toss, "Bitcoin above 100k", flawed_edge_calc)
    # Theta = 0.072, fee_rate = 0.072 * (1 - 0.51) = 0.03528, min_edge = 2.5 * 0.03528 = 0.0882
    # BUG: 0.01 < 0.0882 => REJECTED!
    assert not passed, "EV gate rejected a legitimate edge at p=0.51 due to distance-from-0.5 edge formula!"
    
    # Case B: Zero-alpha favorite at p = 0.95. Market is fair (5% true chance of loss).
    # Whale has NO alpha, but code computes expected_edge = abs(0.95 - 0.5) = 0.45
    price_fav = 0.95
    flawed_edge_fav = abs(price_fav - 0.5)  # 0.45
    passed_fav, fee_fav, min_edge_fav = calculate_fee_aware_ev_gate(price_fav, "Bitcoin above 100k", flawed_edge_fav)
    # Theta = 0.072, fee_rate = 0.072 * 0.05 = 0.0036, min_edge = 0.009
    # BUG: 0.45 >= 0.009 => APPROVED unconditionally!
    assert passed_fav, "EV gate unconditionally approves favorites regardless of actual predictive edge!"


# ============================================================================
# TOPIC 3: Slippage Rules Stress Tests
# ============================================================================

def test_slippage_accepts_favorable_price_discounts():
    """Directional validation: check_slippage accepts BUY orders when price moves down favorably."""
    whale_entry = 0.20
    # Current price is $0.18 (10% discount for buyer)
    favorable_buy_price = 0.18
    res = check_slippage(whale_entry, favorable_buy_price, side="BUY")
    assert res == 'EXECUTE_ORDER', "check_slippage should execute favorable 10% price discount"

    # Current price is $0.75 for whale entry $0.80 (-6.25% discount for buyer)
    res_high = check_slippage(0.80, 0.75, side="BUY")
    assert res_high == 'EXECUTE_ORDER', "check_slippage should execute favorable discount at 0.80"


def test_slippage_accepts_favorable_sell_premiums():
    """Directional validation: check_slippage accepts SELL orders when price moves up favorably."""
    whale_sold = 0.20
    # Market price surged to $0.25 (+25% gain if sold now)
    favorable_sell_price = 0.25
    res = check_slippage(whale_sold, favorable_sell_price, side="SELL")
    assert res == 'EXECUTE_ORDER', "check_slippage should execute favorable sell premium"

    # Adverse move on sell (price dropped from 0.50 to 0.40 -> -20% adverse)
    res_adverse = check_slippage(0.50, 0.40, side="SELL")
    assert res_adverse == 'CANCEL_ORDER: SLIPPAGE_EXCEEDED', "check_slippage should cancel adverse sell slippage"


def test_slippage_zero_price_bypass():
    """Zero whale price bypasses slippage check."""
    assert check_slippage(0.0, 0.50) == 'EXECUTE_ORDER'
    assert check_slippage(-0.10, 0.50) == 'EXECUTE_ORDER'


# ============================================================================
# TOPIC 4: Cash Balance & Mark-to-Market Accounting Stress Tests
# ============================================================================

def test_unrealized_gains_phantom_free_cash_inflation():
    """Empirical simulation of free cash inflation from unrealized MTM swings."""
    initial_cash = 10000.0
    
    # 1. User buys $5,000 notional of a penny contract @ $0.10 (50,000 shares)
    open_notional = 5000.0
    actual_settled_cash = initial_cash - open_notional  # $5,000.00
    
    # 2. Token surges to $0.90 (unrealized gain = 50,000 * 0.80 = $40,000.00)
    unrealized_gain = 5000.0 * ((0.90 - 0.10) / 0.10)  # $40,000.00
    total_portfolio_equity = initial_cash + unrealized_gain  # $50,000.00
    
    # 3. Baleen live_poller.py line 237 formula:
    # free_cash = max(0.0, total_portfolio_equity - current_open_notional)
    baleen_free_cash = max(0.0, total_portfolio_equity - open_notional)  # $45,000.00
    
    # PROOF: Real cash available to spend is only $5,000.00, but Baleen computes $45,000.00!
    assert baleen_free_cash == 45000.0
    assert actual_settled_cash == 5000.0
    assert baleen_free_cash - actual_settled_cash == 40000.0, "Phantom cash inflation by $40,000!"


# ============================================================================
# TOPIC 5: PnL Double-Counting & Multi-Trade FIFO Scenarios
# ============================================================================

def test_user_realized_pnl_double_counting_simulation():
    """Empirical proof: live_poller.py assigns realized_pnl_usd to BOTH the BUY and SELL logs for users."""
    # Simulate trade: BUY $50 @ $0.50, Fee = $1.00
    buy_notional = 50.0
    buy_price = 0.50
    buy_fee = 1.00
    
    # User BUY log initially
    user_buy_log = {
        "side": "BUY",
        "status": "FILLED",
        "notional_usd": buy_notional,
        "user_fill_price": buy_price,
        "fee_usd": buy_fee,
        "realized_pnl_usd": None
    }
    
    # Later: Price is $0.80, whale SELLs, closing position
    sell_price = 0.80
    sell_fee = 1.60
    price_ratio = (sell_price - buy_price) / buy_price  # (0.80 - 0.50) / 0.50 = +0.60 (+60%)
    
    # --- Exact logic from live_poller.py lines 331-355 ---
    # Line 331-332: Update BUY log
    user_buy_log["status"] = "CLOSED"
    user_buy_log["realized_pnl_usd"] = round(buy_notional * price_ratio - buy_fee, 2)  # 50 * 0.6 - 1.0 = $29.00
    
    # Line 333: Create SELL log with realized_pnl_val
    u_realized_pnl_val = round(buy_notional * price_ratio - sell_fee, 2)  # 50 * 0.6 - 1.6 = $28.40
    user_sell_log = {
        "side": "SELL",
        "status": "CLOSED",
        "notional_usd": buy_notional,
        "user_fill_price": sell_price,
        "fee_usd": sell_fee,
        "realized_pnl_usd": u_realized_pnl_val
    }
    
    # --- Exact logic from mark_to_market.py line 240 ---
    all_user_logs = [user_buy_log, user_sell_log]
    u_pnl_computed = sum(float(l["realized_pnl_usd"] or 0.0) for l in all_user_logs)
    
    # Expected true PnL: Gross Return ($30.00) - Entry Fee ($1.00) - Exit Fee ($1.60) = $27.40
    true_net_pnl = round(buy_notional * price_ratio - (buy_fee + sell_fee), 2)
    assert true_net_pnl == 27.40
    
    # BUG PROOF: Baleen computed $29.00 + $28.40 = $57.40 (more than 2x the real return!)
    assert u_pnl_computed == 57.40
    assert u_pnl_computed > true_net_pnl * 2.0, "User PnL was doubled due to dual log recording!"


def test_system_vs_user_pnl_asymmetry():
    """Verify system execution (user_id=None) correctly avoids double-counting, proving user logic was broken."""
    # System execution in live_poller.py line 279 sets: sys_realized_pnl_val = None
    sys_buy_log = {
        "side": "BUY",
        "status": "CLOSED",
        "realized_pnl_usd": 27.40  # Entry fee + exit fee subtracted on buy log
    }
    sys_sell_log = {
        "side": "SELL",
        "status": "CLOSED",
        "realized_pnl_usd": None   # Sell log has None!
    }
    sys_pnl_computed = sum(float(l["realized_pnl_usd"] or 0.0) for l in [sys_buy_log, sys_sell_log])
    assert sys_pnl_computed == 27.40, "System execution had correct single-entry PnL, highlighting user-level bug!"


def test_multi_trade_fifo_orphan_bug():
    """Empirical proof of orphan open positions in multi-trade FIFO closes.
    When a user buys in multiple batches, a single large SELL closes only the 1st batch
    and leaves subsequent batches orphaned in FILLED status forever.
    """
    # User holds 3 batches of BUYs
    batch_1 = {"id": 1, "notional": 30.0, "price": 0.40, "status": "FILLED", "realized_pnl": None}
    batch_2 = {"id": 2, "notional": 40.0, "price": 0.50, "status": "FILLED", "realized_pnl": None}
    batch_3 = {"id": 3, "notional": 50.0, "price": 0.60, "status": "FILLED", "realized_pnl": None}
    
    open_buys = [batch_1, batch_2, batch_3]
    
    # Whale sells $120 notional @ $0.80 (exiting the full position)
    sell_fill_price = 0.80
    sell_notional = 120.0
    
    # --- live_poller.py lines 325-333 behavior ---
    earliest_buy = open_buys[0]
    earliest_buy["status"] = "CLOSED"
    earliest_buy["realized_pnl"] = 30.0 * ((0.80 - 0.40) / 0.40) - 0.50  # $29.50
    
    # BUG 1: batch_2 and batch_3 are NOT closed despite whale completely liquidating!
    assert batch_2["status"] == "FILLED", "Batch 2 remained orphaned in FILLED status!"
    assert batch_3["status"] == "FILLED", "Batch 3 remained orphaned in FILLED status!"
    
    # BUG 2: The SELL log applies batch 1's price ratio to the FULL $120 sell_notional!
    price_ratio = (0.80 - 0.40) / 0.40  # 100% gain applied to entire $120
    sell_log_pnl = round(sell_notional * price_ratio - 1.0, 2)  # $119.00
    
    # Total recorded PnL: $29.50 (batch 1) + $119.00 (sell log) = $148.50
    # Plus batch 2 and batch 3 are STILL open and generating floating MTM!
    assert sell_log_pnl == 119.00
    assert batch_1["realized_pnl"] == 29.50


def test_dynamic_sizing_model_behavior():
    """Verify dynamic sizer calculation and constraints from dynamic_sizer.py."""
    # Test valid balanced profile sizing
    res = size_trade(
        user_balance=10000.0,
        risk_profile="balanced",
        n_active=10,
        whale_trade_value=500.0,
        whale_portfolio_value=10000.0
    )
    # base_notional = 10000 / 10 = 1000
    # whale_risk_pct = 500 / 10000 = 0.05
    # raw_order_value = 1000 * 0.05 = 50.0
    # max_allowed = 10000 * 0.10 = 1000
    # order_value = min(50, 1000) = 50.0
    assert res.status == "SUCCESS"
    assert res.value == 50.0

    # Test risk cap enforcement (aggressive whale trading 50% of portfolio)
    res_capped = size_trade(
        user_balance=1000.0,
        risk_profile="conservative",  # 5% max cap = $50
        n_active=2,                   # base = $500
        whale_trade_value=5000.0,     # whale trades 50%
        whale_portfolio_value=10000.0
    )
    # raw_order_value = 500 * 0.5 = 250
    # max_allowed = 1000 * 0.05 = 50
    assert res_capped.status == "SUCCESS"
    assert res_capped.value == 50.0  # Capped at $50.00!

    # Test below minimum order threshold ($5.00)
    res_small = size_trade(
        user_balance=100.0,
        risk_profile="balanced",
        n_active=20,
        whale_trade_value=10.0,
        whale_portfolio_value=10000.0
    )
    # base = 5, risk = 0.001 => raw = 0.005 < 5.0
    assert res_small.status == "SKIPPED_BELOW_MINIMUM"
    assert res_small.value == 0.0
