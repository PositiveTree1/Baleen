import pytest
from app.sizing.sleeve_manager import SleeveManager, SleeveAllocation, SleeveSizingResult

def test_sleeve_budget_even_split_10_wallets():
    """Verifies that a $10,000 bankroll splits into exactly $1,000 per sleeve across 10 wallets."""
    bankroll = 10000.0
    budget = SleeveManager.calculate_sleeve_budget(bankroll, active_roster_size=10)
    assert budget == 1000.0

    # Dynamic scaling if bankroll changes
    assert SleeveManager.calculate_sleeve_budget(15000.0, active_roster_size=10) == 1500.0
    assert SleeveManager.calculate_sleeve_budget(0.0, active_roster_size=10) == 0.0

def test_conviction_percentile_sizing():
    """
    Verifies that trade size ranks against trailing trade history (0.05 to 1.0)
    and sizes proportionally to the remaining sleeve.
    """
    trailing = [10.0, 20.0, 50.0, 100.0, 500.0]
    
    # Trade of $50 is at the median (3/5 = 60th percentile)
    p_med = SleeveManager.calculate_conviction_percentile(50.0, trailing)
    assert p_med == 0.60

    # Huge trade of $1000 is top conviction (5/5 = 100th percentile)
    p_max = SleeveManager.calculate_conviction_percentile(1000.0, trailing)
    assert p_max == 1.0

    # Tiny trade of $5 is feeler (0/5 -> clamped to 0.05)
    p_min = SleeveManager.calculate_conviction_percentile(5.0, trailing)
    assert p_min == 0.05

def test_sleeve_isolation_no_starvation():
    """
    Verifies that one wallet exhausting its sleeve does NOT starve or clip
    a different wallet's trade.
    """
    # Wallet A has used $950 of its $1,000 sleeve ($50 remaining)
    res_a = SleeveManager.size_sleeve_trade(
        wallet_address="0xAAAA",
        whale_trade_size_usd=500.0,
        sleeve_budget_usd=1000.0,
        open_notional_usd=950.0,
        trailing_sizes=[100.0, 200.0, 300.0, 400.0, 500.0]
    )
    # Intended is $50 * 1.0 = $50, actual is $50 (fits remaining)
    assert res_a.actual_size_usd == 50.0
    assert res_a.status == "SUCCESS"

    # Wallet B has fresh $1,000 sleeve ($0 open notional)
    res_b = SleeveManager.size_sleeve_trade(
        wallet_address="0xBBBB",
        whale_trade_size_usd=500.0,
        sleeve_budget_usd=1000.0,
        open_notional_usd=0.0,
        trailing_sizes=[100.0, 200.0, 300.0, 400.0, 500.0]
    )
    # Intended is $1000 * 1.0 = $1000, actual is $1000 (full size, not starved by A!)
    assert res_b.actual_size_usd == 1000.0
    assert res_b.status == "SUCCESS"

def test_copy_pnl_ema_adjustment_and_floor():
    """
    Verifies slow EMA copy-PnL adjustment and strict 0.30x ($300) floor.
    """
    base_budget = 1000.0

    # Neutral copy-PnL -> 1.0x ($1,000)
    assert SleeveManager.calculate_adjusted_sleeve_budget(base_budget, 0.0) == 1000.0

    # Positive copy-PnL (+$250) -> scales up to 1.50x cap ($1,500)
    adj_pos = SleeveManager.calculate_adjusted_sleeve_budget(base_budget, 250.0)
    assert adj_pos == 1500.0

    # Massive losing copy-PnL (-$800) -> clamped at 0.30x ($300 floor, never zero!)
    adj_neg = SleeveManager.calculate_adjusted_sleeve_budget(base_budget, -800.0)
    assert adj_neg == 300.0

    # Slow EMA update with alpha=0.05
    new_ema = SleeveManager.update_copy_pnl_ema(current_ema=50.0, new_realized_pnl=-20.0, alpha=0.05)
    assert new_ema == round(0.95 * 50.0 + 0.05 * (-20.0), 4)

def test_capture_rate_calculation_and_clipping():
    """
    Verifies capture rate logging when a signal is clipped due to sleeve limits.
    """
    # Sleeve has $40 remaining. Whale puts a huge conviction trade intended for $100.
    res = SleeveManager.size_sleeve_trade(
        wallet_address="0xCCCC",
        whale_trade_size_usd=1000.0,
        sleeve_budget_usd=1000.0,
        open_notional_usd=960.0,  # $40 remaining
        trailing_sizes=[100.0, 200.0],
        min_trade_usd=5.0
    )
    assert res.actual_size_usd == 40.0
    assert res.is_clipped == True
    # Capture rate is 40 / 1000 = 4.0% of intended signal
    assert res.capture_rate_pct == 4.0
