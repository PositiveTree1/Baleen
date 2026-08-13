from app.sizing.dynamic_sizer import size_trade

def test_sizing_scales_with_active_basket_size():
    # User balance 10,000, 10 active wallets. Base = 1,000.
    # Whale risks 5% of portfolio (5k / 100k).
    # Order = 1000 * 0.05 = 50.
    res1 = size_trade(10000.0, 'balanced', 10, 5000.0, 100000.0)
    assert res1.value == 50.0
    
    # 5 active wallets. Base = 2,000.
    # Order = 2000 * 0.05 = 100.
    res2 = size_trade(10000.0, 'balanced', 5, 5000.0, 100000.0)
    assert res2.value == 100.0

def test_risk_cap_overrides_raw_calculation():
    # Base = 1000 (10k / 10). Whale risks 50%.
    # Raw = 500. Balanced cap = 10% of 10k = 1000. Raw < Cap.
    res = size_trade(10000.0, 'balanced', 10, 50000.0, 100000.0)
    assert res.value == 500.0
    
    # Now Conservative cap = 5% of 10k = 500.
    # Raw is 500, cap is 500.
    # What if Raw is 1000? Base = 1000, Whale risks 100%. Raw = 1000. Cap = 500.
    res_capped = size_trade(10000.0, 'conservative', 10, 100000.0, 100000.0)
    assert res_capped.value == 500.0

def test_below_minimum_is_skipped_not_failed():
    # Whale risks 0.01%. Raw = 0.1
    res = size_trade(10000.0, 'balanced', 10, 10.0, 100000.0, min_order_usd=5.0)
    assert res.value == 0
    assert res.status == 'SKIPPED_BELOW_MINIMUM'

def test_dormant_wallets_excluded_from_denominator():
    # If there are 10 active + 5 dormant, only 10 are passed to sizing func.
    res = size_trade(10000.0, 'balanced', 10, 5000.0, 100000.0)
    assert res.value == 50.0

def test_equal_weight_across_active_members():
    res1 = size_trade(10000.0, 'balanced', 4, 1000.0, 10000.0)
    res2 = size_trade(10000.0, 'balanced', 4, 1000.0, 10000.0)
    # Different trades, same relative risk (10%), same base (2500)
    assert res1.value == res2.value == 250.0
