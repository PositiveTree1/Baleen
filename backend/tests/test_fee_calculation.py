def calculate_fee(hwm: float, current_value: float, fee_pct: float = 0.20):
    if current_value <= hwm:
        return 0.0, hwm
    
    profit = current_value - hwm
    fee = profit * fee_pct
    new_hwm = current_value - fee # Or current_value depending on exact logic. Let's assume hwm just goes up to current_value
    return fee, current_value

def test_no_fee_when_recovering_past_losses():
    # HWM is 10k. Value drops to 8k, then recovers to 9.5k.
    fee, new_hwm = calculate_fee(10000.0, 9500.0)
    assert fee == 0.0
    assert new_hwm == 10000.0

def test_fee_only_on_profit_above_hwm():
    # HWM is 10k. Value is 11k.
    fee, new_hwm = calculate_fee(10000.0, 11000.0)
    assert fee == 200.0 # 20% of 1000
    assert new_hwm == 11000.0

def test_hwm_ratchets_up_only():
    # Drops
    _, hwm1 = calculate_fee(10000.0, 9000.0)
    assert hwm1 == 10000.0
    
    # Rises above
    _, hwm2 = calculate_fee(10000.0, 12000.0)
    assert hwm2 == 12000.0
