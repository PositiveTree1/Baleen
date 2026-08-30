import pytest
from app.sizing.slippage import calculate_simulated_fill_price, check_slippage
from app.sizing.sleeve_manager import SleeveManager

def test_universal_simulated_fill_price_slippage():
    # BUY slippage should increase entry price
    p_buy = calculate_simulated_fill_price(price=0.35558, side="BUY", notional_usd=250.0)
    assert p_buy > 0.35558
    assert round(p_buy, 4) != round(0.35558, 4)

    # SELL slippage should decrease exit price
    p_sell = calculate_simulated_fill_price(price=0.95879, side="SELL", notional_usd=500.0)
    assert p_sell < 0.95879
    assert round(p_sell, 4) != round(0.95879, 4)

    # Extreme low prices should still have distinct slippage
    p_low = calculate_simulated_fill_price(price=0.05, side="BUY", notional_usd=50.0)
    assert p_low > 0.05
    assert round(abs(p_low - 0.05), 5) >= 0.0001

def test_sleeve_budget_sample_size_damping_sits_to_pee():
    # SitsToPee scenario: 2 trades, 100% win rate, low trade count
    # Base budget: $1,000, copy_pnl_ema: $0.0, baleen_score: 25.0
    budget_n2 = SleeveManager.calculate_adjusted_sleeve_budget(
        base_budget=1000.0,
        copy_pnl_ema=0.0,
        baleen_score=25.0,
        trades_analyzed=2
    )
    # Must NOT be slashed to $300; must stay near base $900-$1,100
    assert budget_n2 >= 900.0
    assert budget_n2 <= 1100.0

    # abdkxrhxr scenario: 18 trades, score 89.0, positive copy PnL
    budget_n18 = SleeveManager.calculate_adjusted_sleeve_budget(
        base_budget=1000.0,
        copy_pnl_ema=150.0,
        baleen_score=89.0,
        trades_analyzed=18
    )
    assert budget_n18 > 1000.0
    assert budget_n18 <= 1500.0

def test_sleeve_budget_edge_cases():
    # Zero base budget
    assert SleeveManager.calculate_adjusted_sleeve_budget(base_budget=0.0) == 0.0
    
    # Negative base budget
    assert SleeveManager.calculate_adjusted_sleeve_budget(base_budget=-100.0) == 0.0
    
    # High score with high sample
    budget_max = SleeveManager.calculate_adjusted_sleeve_budget(
        base_budget=1000.0,
        copy_pnl_ema=500.0,
        baleen_score=100.0,
        trades_analyzed=50
    )
    assert budget_max <= 1500.0
    assert budget_max >= 1200.0

