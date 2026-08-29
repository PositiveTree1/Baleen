"""
Empirical Stress Test Harness: 2026 Quadratic Fee Schedule Boundary & Matrix Validation
Challenger 2 for Milestone M-A1
"""

import decimal
import math
import pytest
from app.services.polymarket_fees import (
    classify_market_category,
    calculate_polymarket_fee,
    calculate_fee_aware_ev_gate,
    _CRYPTO_KEYWORDS,
    _ECONOMICS_FINANCE_KEYWORDS,
    _CULTURE_TECH_KEYWORDS,
    _POLITICS_KEYWORDS,
    _SPORTS_KEYWORDS,
    _GEOPOLITICS_KEYWORDS,
)

# 6 Official Categories with test market titles and expected Thetas
CATEGORIES_MATRIX = [
    ("Crypto", "Bitcoin hit $150k before December?", 0.072),
    ("Economics / Finance", "US Federal Reserve interest rate cut in September?", 0.060),
    ("Culture, Weather & Tech", "OpenAI releases GPT-5 in 2026?", 0.050),
    ("Politics", "US Presidential Election Winner 2028?", 0.040),
    ("Sports", "Arsenal vs Chelsea Premier League winner?", 0.030),
    ("Geopolitics", "Ceasefire agreement treaty in Ukraine?", 0.000),
]

BOUNDARY_PRICES = [
    (0.00, 0.001),     # Clamped to 0.001
    (0.001, 0.001),   # Exact lower boundary
    (0.50, 0.50),     # Midpoint
    (0.999, 0.999),   # Exact upper boundary
    (1.00, 0.999),    # Clamped to 0.999
    (-0.50, 0.001),   # Negative clamped to 0.001
    (1.50, 0.999),    # Above 1 clamped to 0.999
    (None, 0.50),     # None defaults to 0.50
]

NOTIONAL_VALUES = [
    0.0,
    -100.0,
    0.01,
    0.50,
    1.00,
    10.00,
    50.00,
    100.00,
    500.00,
    1000.00,
    10000.00,
    1000000.00,
    1e9,
]


def test_matrix_all_categories_and_boundary_prices():
    """
    Stress-test full cartesian product: 6 categories x 8 boundary prices x 6 notionals.
    Validates exact 2026 quadratic formula: Fee = Notional * Theta * (1 - p_clamped)
    """
    for cat_name, title, theta in CATEGORIES_MATRIX:
        # Category classification verification
        detected_cat, detected_theta = classify_market_category(title)
        assert detected_cat == cat_name
        assert math.isclose(detected_theta, theta, abs_tol=1e-6)

        for price_in, p_expected in BOUNDARY_PRICES:
            for notional in [1.0, 10.0, 100.0, 1000.0, 50000.0]:
                res = calculate_polymarket_fee(notional, price_in, title, is_maker=False)

                assert res["category"] == cat_name
                assert math.isclose(res["category_rate"], theta, abs_tol=1e-6)
                assert res["is_maker"] is False

                if theta == 0.0:
                    assert res["fee_usd"] == 0.0
                    assert res["effective_fee_pct"] == 0.0
                    assert res["maker_rebate_eligible"] is True
                else:
                    assert res["maker_rebate_eligible"] is False
                    raw_expected = notional * theta * (1.0 - p_expected)
                    d_expected = decimal.Decimal(str(raw_expected)).quantize(
                        decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_EVEN
                    )
                    expected_fee = float(d_expected)

                    assert res["fee_usd"] == expected_fee, (
                        f"Mismatch for {cat_name} at price={price_in} (p={p_expected}), "
                        f"notional={notional}: expected {expected_fee}, got {res['fee_usd']}"
                    )

                    expected_pct = round((expected_fee / notional) * 100.0, 3)
                    assert math.isclose(res["effective_fee_pct"], expected_pct, abs_tol=1e-3)


def test_specific_boundary_price_points():
    """
    Test exact numerical outputs specified in prompt:
    Prices: $0.00, $0.001, $0.50, $0.999, $1.00 across $100 notional.
    """
    test_cases = [
        # (Price, Category, Expected Fee USD, Expected Effective %)
        # 1. Crypto (Theta = 0.072)
        (0.00, "Crypto", "Bitcoin hit $100k", 7.19, 7.19),       # 100 * 0.072 * 0.999 = 7.1928 -> 7.19
        (0.001, "Crypto", "Bitcoin hit $100k", 7.19, 7.19),      # 100 * 0.072 * 0.999 = 7.1928 -> 7.19
        (0.50, "Crypto", "Bitcoin hit $100k", 3.60, 3.60),       # 100 * 0.072 * 0.500 = 3.6000 -> 3.60
        (0.999, "Crypto", "Bitcoin hit $100k", 0.01, 0.01),      # 100 * 0.072 * 0.001 = 0.0072 -> 0.01
        (1.00, "Crypto", "Bitcoin hit $100k", 0.01, 0.01),       # 100 * 0.072 * 0.001 = 0.0072 -> 0.01

        # 2. Economics / Finance (Theta = 0.060)
        (0.00, "Economics / Finance", "Fed rate cut", 5.99, 5.99), # 100 * 0.060 * 0.999 = 5.994 -> 5.99
        (0.001, "Economics / Finance", "Fed rate cut", 5.99, 5.99),
        (0.50, "Economics / Finance", "Fed rate cut", 3.00, 3.00), # 100 * 0.060 * 0.500 = 3.00
        (0.999, "Economics / Finance", "Fed rate cut", 0.01, 0.01),# 100 * 0.060 * 0.001 = 0.006 -> 0.01
        (1.00, "Economics / Finance", "Fed rate cut", 0.01, 0.01),

        # 3. Culture, Weather & Tech (Theta = 0.050)
        (0.00, "Culture, Weather & Tech", "OpenAI model", 5.00, 5.00), # 100 * 0.050 * 0.999 = 4.995 -> 5.00
        (0.001, "Culture, Weather & Tech", "OpenAI model", 5.00, 5.00),
        (0.50, "Culture, Weather & Tech", "OpenAI model", 2.50, 2.50),  # 100 * 0.050 * 0.50 = 2.50
        (0.999, "Culture, Weather & Tech", "OpenAI model", 0.01, 0.01), # Float IEEE 1 - 0.999 = 0.0010000000000000009 -> 0.0050000000000000045 -> 0.01
        (1.00, "Culture, Weather & Tech", "OpenAI model", 0.01, 0.01),

        # 4. Politics (Theta = 0.040)
        (0.00, "Politics", "Presidential Election", 4.00, 4.00),   # 100 * 0.040 * 0.999 = 3.996 -> 4.00
        (0.001, "Politics", "Presidential Election", 4.00, 4.00),
        (0.50, "Politics", "Presidential Election", 2.00, 2.00),   # 100 * 0.040 * 0.50 = 2.00
        (0.999, "Politics", "Presidential Election", 0.00, 0.00),  # 100 * 0.040 * 0.001 = 0.004 -> 0.00
        (1.00, "Politics", "Presidential Election", 0.00, 0.00),

        # 5. Sports (Theta = 0.030)
        (0.00, "Sports", "Arsenal vs Chelsea", 3.00, 3.00),        # 100 * 0.030 * 0.999 = 2.997 -> 3.00
        (0.001, "Sports", "Arsenal vs Chelsea", 3.00, 3.00),
        (0.50, "Sports", "Arsenal vs Chelsea", 1.50, 1.50),        # 100 * 0.030 * 0.50 = 1.50
        (0.999, "Sports", "Arsenal vs Chelsea", 0.00, 0.00),       # 100 * 0.030 * 0.001 = 0.003 -> 0.00
        (1.00, "Sports", "Arsenal vs Chelsea", 0.00, 0.00),

        # 6. Geopolitics (Theta = 0.000)
        (0.00, "Geopolitics", "Ukraine Ceasefire", 0.00, 0.00),
        (0.001, "Geopolitics", "Ukraine Ceasefire", 0.00, 0.00),
        (0.50, "Geopolitics", "Ukraine Ceasefire", 0.00, 0.00),
        (0.999, "Geopolitics", "Ukraine Ceasefire", 0.00, 0.00),
        (1.00, "Geopolitics", "Ukraine Ceasefire", 0.00, 0.00),
    ]

    for price, cat, title, exp_fee, exp_pct in test_cases:
        res = calculate_polymarket_fee(100.0, price, title)
        raw = 100.0 * res["category_rate"] * (1.0 - max(0.001, min(0.999, price)))
        d_val = decimal.Decimal(str(raw)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_EVEN)
        expected_rounded = float(d_val)
        
        assert res["fee_usd"] == expected_rounded == exp_fee, (
            f"Price {price} for {cat}: got fee_usd={res['fee_usd']}, "
            f"expected_rounded={expected_rounded}, table exp_fee={exp_fee}"
        )
        assert res["effective_fee_pct"] == exp_pct


def test_maker_zero_fee_invariant_across_all_boundaries():
    """Verify Maker orders NEVER incur fees under any circumstance."""
    for cat_name, title, _ in CATEGORIES_MATRIX:
        for price_in, _ in BOUNDARY_PRICES:
            for notional in NOTIONAL_VALUES:
                res = calculate_polymarket_fee(notional, price_in, title, is_maker=True)
                assert res["fee_usd"] == 0.0
                assert res["effective_fee_pct"] == 0.0
                assert res["is_maker"] is True
                assert res["maker_rebate_eligible"] is True


def test_zero_and_negative_notional_invariant():
    """Verify zero and negative notionals safely return 0.0 fee without error."""
    for cat_name, title, _ in CATEGORIES_MATRIX:
        for notional in [0.0, -0.01, -1.0, -100.0, -1e6]:
            res_taker = calculate_polymarket_fee(notional, 0.50, title, is_maker=False)
            assert res_taker["fee_usd"] == 0.0
            assert res_taker["effective_fee_pct"] == 0.0
            assert res_taker["maker_rebate_eligible"] is True

            res_maker = calculate_polymarket_fee(notional, 0.50, title, is_maker=True)
            assert res_maker["fee_usd"] == 0.0
            assert res_maker["effective_fee_pct"] == 0.0
            assert res_maker["maker_rebate_eligible"] is True


def test_bankers_rounding_half_to_even_rigorous():
    """
    Rigorously test ROUND_HALF_EVEN behavior on exact midpoints (.005).
    """
    for i in range(10):
        val_str = f"0.{i:02d}5"
        d = decimal.Decimal(val_str).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_EVEN)
        expected_even_cent = (i if i % 2 == 0 else i + 1) / 100.0
        assert float(d) == expected_even_cent, f"{val_str} quantized to {d}, expected {expected_even_cent}"


def test_fee_monotonicity_with_price():
    """
    Fee should be monotonically non-increasing as price increases from 0.001 to 0.999.
    At higher probability (price -> 1.0), risk is lower so Polymarket charges lower fee.
    """
    notional = 1000.0
    for cat_name, title, theta in CATEGORIES_MATRIX:
        if theta == 0.0:
            continue
        prev_fee = float('inf')
        for p_int in range(1, 1000, 5):  # 0.001 to 0.999
            p = p_int / 1000.0
            res = calculate_polymarket_fee(notional, p, title)
            fee = res["fee_usd"]
            assert fee <= prev_fee + 1e-9, f"Monotonicity violated at p={p} for {cat_name}: {fee} > {prev_fee}"
            prev_fee = fee


def test_ev_net_gate_stress_matrix():
    """
    Stress-test EV Gate across boundary prices and edge conditions.
    Gate rule: expected_edge >= 2.5 * Theta * (1 - p)
    """
    for cat_name, title, theta in CATEGORIES_MATRIX:
        for price_in, p_clamped in BOUNDARY_PRICES:
            expected_fee_rate = theta * (1.0 - p_clamped)
            expected_min_edge = 2.5 * expected_fee_rate

            # 1. Edge exactly at threshold
            passed, f_rate, min_edge = calculate_fee_aware_ev_gate(price_in, title, expected_min_edge)
            assert passed is True
            assert math.isclose(f_rate, round(expected_fee_rate, 4), abs_tol=1e-4)
            assert math.isclose(min_edge, round(expected_min_edge, 4), abs_tol=1e-4)

            # 2. Edge slightly below threshold
            if expected_min_edge > 0.0001:
                passed_below, _, _ = calculate_fee_aware_ev_gate(price_in, title, expected_min_edge - 0.0001)
                assert passed_below is False

            # 3. Edge significantly above threshold
            passed_above, _, _ = calculate_fee_aware_ev_gate(price_in, title, expected_min_edge + 0.10)
            assert passed_above is True


def test_category_classification_stress_and_precedence():
    """
    Test classification edge cases:
    - Case insensitivity
    - Extra whitespace
    - Empty and None titles
    - Precedence: Geopolitics > Crypto > Economics > Politics > Sports > Culture > General
    """
    # Empty / None -> General (0.050)
    assert classify_market_category("") == ("General", 0.050)
    assert classify_market_category(None) == ("General", 0.050)
    assert classify_market_category("   ") == ("General", 0.050)

    # Case insensitivity
    assert classify_market_category("BITCOIN PRICE ABOVE 100K") == ("Crypto", 0.072)
    assert classify_market_category("fed interest rate decision") == ("Economics / Finance", 0.060)
    assert classify_market_category("TRUMP ELECTORAL COLLEGE") == ("Politics", 0.040)
    assert classify_market_category("REAL MADRID VS BARCELONA") == ("Sports", 0.030)
    assert classify_market_category("UKRAINE WAR CEASEFIRE") == ("Geopolitics", 0.000)

    # Precedence: Geopolitics keyword overrides others
    cat_overlap, theta_overlap = classify_market_category("War impact on Bitcoin and crypto markets")
    assert cat_overlap == "Geopolitics"
    assert theta_overlap == 0.000


def test_float_edge_cases_and_extreme_notionals():
    """
    Stress test extreme numerical and string float representations:
    - String price input (e.g. "0.50")
    - Decimal price input
    - Extreme high notional ($1B)
    - Extreme low notional ($0.00001)
    """
    # String prices
    res_str = calculate_polymarket_fee(100.0, "0.50", "Bitcoin hit $100k")
    assert res_str["fee_usd"] == 3.60

    # Decimal prices
    res_dec = calculate_polymarket_fee(100.0, decimal.Decimal("0.50"), "Bitcoin hit $100k")
    assert res_dec["fee_usd"] == 3.60

    # $1 Billion notional at p=0.50 for Crypto
    res_billion = calculate_polymarket_fee(1_000_000_000.0, 0.50, "Bitcoin hit $100k")
    assert res_billion["fee_usd"] == 36_000_000.0
    assert res_billion["effective_fee_pct"] == 3.60

    # Micro notional $0.0001 (fraction of a cent)
    res_micro = calculate_polymarket_fee(0.0001, 0.50, "Bitcoin hit $100k")
    assert res_micro["fee_usd"] == 0.0
    assert res_micro["effective_fee_pct"] == 0.0
