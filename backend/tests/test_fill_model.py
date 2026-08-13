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
