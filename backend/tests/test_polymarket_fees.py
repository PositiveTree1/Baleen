"""
Unit tests for Polymarket Dynamic Fee Schedule (2026 Spec) & Zero-Price Contract Handling.
"""

import math
import pytest
from app.services.polymarket_fees import (
    classify_market_category,
    calculate_polymarket_fee,
    calculate_fee_aware_ev_gate,
)


def test_zero_price_contract_fee_clamp():
    """
    Verify price == 0.0 clamps strictly to 0.001 (NOT falling back to 0.50).
    For Crypto (Theta = 0.072), $100 notional:
    - At p = 0.0 (clamped to 0.001): Fee = 100 * 0.072 * (1 - 0.001) = 7.1928 -> $7.19.
    - If buggy fallback to 0.50 occurred: Fee would be $3.60.
    """
    fee_crypto = calculate_polymarket_fee(100.0, 0.0, "Bitcoin hit $100k")
    assert fee_crypto["fee_usd"] == 7.19, f"Expected 7.19, got {fee_crypto['fee_usd']}"
    assert fee_crypto["category"] == "Crypto"
    assert math.isclose(fee_crypto["category_rate"], 0.072)


def test_zero_price_contract_ev_gate():
    """
    Verify calculate_fee_aware_ev_gate correctly clamps price == 0.0 to 0.001.
    """
    passed, fee_rate, min_edge = calculate_fee_aware_ev_gate(0.0, "Bitcoin hit $100k", 0.20)
    # Theta = 0.072, p = 0.001 -> fee_rate = 0.072 * (1 - 0.001) = 0.071928 -> 0.0719
    # min_edge = 2.5 * 0.071928 = 0.1798
    assert round(fee_rate, 4) == 0.0719
    assert round(min_edge, 4) == 0.1798
    assert passed is True


def test_none_price_fallback():
    """
    Verify price == None safely falls back to default 0.50.
    """
    fee_res = calculate_polymarket_fee(100.0, None, "Bitcoin hit $100k")
    # At p = 0.50: Fee = 100 * 0.072 * 0.5 = 3.60
    assert fee_res["fee_usd"] == 3.60


def test_extreme_boundary_prices():
    """
    Test extreme boundary prices (0.00001, 1.0, -0.5, 0.999).
    """
    notional = 100.0
    title = "Fed interest rate cut in September"  # Economics theta = 0.060

    # Negative price -> clamped to 0.001
    f_neg = calculate_polymarket_fee(notional, -0.10, title)
    assert f_neg["fee_usd"] == 5.99  # 100 * 0.060 * 0.999 = 5.994 -> 5.99

    # Price = 1.0 -> clamped to 0.999
    f_high = calculate_polymarket_fee(notional, 1.0, title)
    assert f_high["fee_usd"] == 0.01  # 100 * 0.060 * 0.001 = 0.006 -> 0.01

    # Price = 0.999 -> clamped to 0.999
    f_999 = calculate_polymarket_fee(notional, 0.999, title)
    assert f_999["fee_usd"] == 0.01


def test_all_categories_and_maker_rebates():
    """
    Verify maker orders receive $0.00 fee across all categories.
    """
    categories = [
        ("Bitcoin above 100k", "Crypto", 0.072),
        ("CPI inflation announcement", "Economics / Finance", 0.060),
        ("OpenAI releases model", "Culture, Weather & Tech", 0.050),
        ("US Presidential Race", "Politics", 0.040),
        ("Arsenal vs Chelsea", "Sports", 0.030),
        ("Ceasefire agreement in Ukraine", "Geopolitics", 0.000),
    ]

    for title, expected_cat, expected_theta in categories:
        cat, theta = classify_market_category(title)
        assert cat == expected_cat
        assert math.isclose(theta, expected_theta)

        # Maker test
        maker_fee = calculate_polymarket_fee(100.0, 0.50, title, is_maker=True)
        assert maker_fee["fee_usd"] == 0.0
        assert maker_fee["is_maker"] is True
