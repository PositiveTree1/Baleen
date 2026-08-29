from app.sizing.slippage import check_slippage

def test_high_slippage_at_low_price_cancels():
    # Price <= 0.25. Allowed diff > 0.012
    # Whale = 0.20, Current = 0.21 -> diff = 0.05 (5% > 1.2%)
    assert check_slippage(0.20, 0.21) == 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'

def test_low_slippage_at_mid_price_executes():
    # Price <= 0.50. Allowed diff > 0.02
    # Whale = 0.40, Current = 0.405 -> diff = 0.0125 (1.25% < 2%)
    assert check_slippage(0.40, 0.405) == 'EXECUTE_ORDER'

def test_reasonable_slippage_executes():
    # Price > 0.50. Allowed diff > 0.03
    # Whale = 0.80, Current = 0.82 -> diff = 0.025 (2.5% < 3%)
    assert check_slippage(0.80, 0.82) == 'EXECUTE_ORDER'

def test_price_discount_on_buy_executes():
    # BUY order gets a favorable lower entry (0.50 down to 0.45) -> Should execute
    assert check_slippage(0.50, 0.45, side="BUY") == 'EXECUTE_ORDER'

def test_sell_adverse_slippage_cancels():
    # SELL order gets an adverse lower exit (0.50 down to 0.45 -> -10% > 2%) -> Cancel
    assert check_slippage(0.50, 0.45, side="SELL") == 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'

def test_sell_price_improvement_executes():
    # SELL order gets a favorable higher exit (0.50 up to 0.55) -> Should execute
    assert check_slippage(0.50, 0.55, side="SELL") == 'EXECUTE_ORDER'
