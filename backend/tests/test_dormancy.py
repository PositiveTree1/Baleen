from app.scoring.dormancy import check_dormancy

def test_dormancy_is_relative_to_own_median_gap():
    # If median gap is 2 hours, 17 hours is > 8x (16) -> dormant
    assert check_dormancy(17.0, 2.0) is True
    # If median gap is 2 hours, 15 hours is < 8x (16) -> active
    assert check_dormancy(15.0, 2.0) is False

def test_daily_trader_dormant_after_8x_gap():
    # Daily trader (gap 24h). 8 * 24 = 192.
    assert check_dormancy(193.0, 24.0) is True

def test_weekly_trader_not_dormant_at_same_hours():
    # Weekly trader (gap 168h). 8 * 168 = 1344.
    # 193 hours is well within active bounds.
    assert check_dormancy(193.0, 168.0) is False
