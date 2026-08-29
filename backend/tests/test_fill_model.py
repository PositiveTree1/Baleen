from app.sizing.fill_simulator import simulate_fill

def test_fill_walks_order_book_not_exact_whale_price():
    order_book = {
        "asks": [
            {"price": "0.50", "size": "100"},
            {"price": "0.51", "size": "100"}
        ]
    }
    # $75 order.
    # Level 1: 100 shares × $0.50 = $50 of liquidity → takes all 100 shares
    # Level 2: needs $25 more at $0.51 → takes ~49.02 shares
    # Avg price must be > 0.50 (proves book-walking, not exact-price assumption)
    res = simulate_fill(75.0, order_book, "BUY")
    assert res.avg_price > 0.50  # Must reflect book-walking per §13
    assert res.total_filled == 75.0
    assert res.levels_consumed == 2

def test_larger_order_gets_worse_price():
    order_book = {
        "asks": [
            {"price": "0.50", "size": "100"}, # 50 USD
            {"price": "0.51", "size": "100"}  # 51 USD
        ]
    }
    # $75.5 order.
    # Takes all of 0.50 ($50) -> 100 shares.
    # Needs $25.5 more. At 0.51, buys 50 shares.
    # Total shares: 150. Total cost: 75.5.
    # Avg price: 75.5 / 150 = 0.50333
    res = simulate_fill(75.5, order_book, "BUY")
    assert round(res.avg_price, 5) == 0.50333
    assert res.total_filled == 75.5
    assert res.levels_consumed == 2

def test_insufficient_liquidity():
    order_book = {
        "asks": [
            {"price": "0.50", "size": "100"}
        ]
    }
    # Wants $100.
    res = simulate_fill(100.0, order_book, "BUY")
    assert res.total_filled == 50.0 # Only 50 USD available.
    assert res.levels_consumed == 1


def test_fill_simulator_non_mutating_book():
    """Verify order book dictionary and inner level lists are not modified in-place."""
    order_book = {
        "asks": [
            {"price": "0.60", "size": "50"},
            {"price": "0.40", "size": "50"}
        ],
        "bids": [
            {"price": "0.30", "size": "50"},
            {"price": "0.50", "size": "50"}
        ]
    }
    # BUY execution
    res_buy = simulate_fill(20.0, order_book, "BUY")
    assert order_book["asks"][0]["price"] == "0.60"
    assert order_book["asks"][1]["price"] == "0.40"
    assert res_buy.avg_price == 0.40

    # SELL execution
    res_sell = simulate_fill(20.0, order_book, "SELL")
    assert order_book["bids"][0]["price"] == "0.30"
    assert order_book["bids"][1]["price"] == "0.50"
    assert res_sell.avg_price == 0.50


def test_fill_simulator_case_insensitivity():
    """Verify side is handled case-insensitively ('buy', 'BUY', 'bUy', 'sell', 'SELL', 'sElL')."""
    order_book = {
        "asks": [{"price": "0.55", "size": "100"}],
        "bids": [{"price": "0.45", "size": "100"}]
    }
    for buy_side in ["buy", "BUY", "Buy", "bUy"]:
        res = simulate_fill(10.0, order_book, buy_side)
        assert res.avg_price == 0.55
        assert res.total_filled == 10.0

    for sell_side in ["sell", "SELL", "Sell", "sElL"]:
        res = simulate_fill(10.0, order_book, sell_side)
        assert res.avg_price == 0.45
        assert res.total_filled == 10.0


def test_fill_simulator_zero_division_guard():
    """Verify order books with zero price, negative price, or zero size do not cause ZeroDivisionError."""
    corrupted_book = {
        "asks": [
            {"price": "0.0", "size": "100"},
            {"price": "-0.5", "size": "50"},
            {"price": "0.50", "size": "0"},
            {"price": "0.60", "size": "100"}
        ]
    }
    # Should safely skip 0.0, -0.5, and 0-size levels and consume from 0.60
    res = simulate_fill(30.0, corrupted_book, "BUY")
    assert res.avg_price == 0.60
    assert res.total_filled == 30.0
    assert res.levels_consumed == 1


def test_fill_simulator_all_zero_price_levels():
    """Verify order book with only zero-price levels returns empty FillResult safely."""
    zero_book = {
        "asks": [
            {"price": "0.0", "size": "100"},
            {"price": "0.00", "size": "200"}
        ]
    }
    res = simulate_fill(50.0, zero_book, "BUY")
    assert res.avg_price == 0.0
    assert res.total_filled == 0.0
    assert res.levels_consumed == 0

