import time
from datetime import datetime, timezone
import pytest

from app.discovery.scanner import calculate_authentic_wallet_stats
from app.scoring.engine import score_wallet
from app.sizing.dynamic_sizer import calculate_pure_proportional_order_size, size_trade


def test_trade_count_under_100_rejected():
    stats = {
        "all_time_pnl_usd": 150000.0,
        "total_volume_usd": 300000.0,
        "trades_count": 85,  # Under 100 lifetime trades
        "active_days": 60.0,
        "trades_per_day": 1.4,
        "win_rate_pct": 85.0,
        "max_drawdown_pct": 8.0,
        "cumulative_pnl": 150000.0,
    }
    result = score_wallet(stats)
    assert result.status == "rejected"
    assert result.rejection_reason == "INSUFFICIENT_TRADES_UNDER_100"


def test_inactive_past_week_rejected():
    stats = {
        "all_time_pnl_usd": 150000.0,
        "total_volume_usd": 300000.0,
        "trades_count": 250,
        "active_days": 90.0,
        "trades_per_day": 2.7,
        "win_rate_pct": 85.0,
        "max_drawdown_pct": 8.0,
        "cumulative_pnl": 150000.0,
        "is_inactive_7d": True,
    }
    result = score_wallet(stats)
    assert result.status == "rejected"
    assert result.rejection_reason == "INACTIVE_NO_TRADES_IN_PAST_WEEK"


def test_hft_rate_exceeded_50_per_day_rejected():
    stats = {
        "all_time_pnl_usd": 150000.0,
        "total_volume_usd": 300000.0,
        "trades_count": 5000,
        "active_days": 80.0,
        "trades_per_day": 62.5,  # > 50 trades/day
        "is_hft": True,
        "win_rate_pct": 85.0,
        "max_drawdown_pct": 8.0,
        "cumulative_pnl": 150000.0,
    }
    result = score_wallet(stats)
    assert result.status == "rejected"
    assert result.rejection_reason == "HFT_BOT_EXCEEDED_50_PER_DAY"


def test_conflicting_positions_detected():
    stats = {
        "all_time_pnl_usd": 200000.0,
        "total_volume_usd": 500000.0,
        "trades_count": 250,
        "active_days": 80.0,
        "trades_per_day": 3.1,
        "win_rate_pct": 88.0,
        "max_drawdown_pct": 6.0,
        "cumulative_pnl": 200000.0,
        "is_conflicting_positions": True,
    }
    result = score_wallet(stats)
    assert result.status == "rejected"
    assert result.rejection_reason == "CONFLICTING_POSITIONS_DETECTED"


def test_boundary_arbitrage_bot_rejected():
    stats = {
        "all_time_pnl_usd": 120000.0,
        "total_volume_usd": 400000.0,
        "trades_count": 350,
        "active_days": 70.0,
        "trades_per_day": 5.0,
        "win_rate_pct": 92.0,
        "max_drawdown_pct": 5.0,
        "cumulative_pnl": 120000.0,
        "is_boundary_arb": True,
    }
    result = score_wallet(stats)
    assert result.status == "rejected"
    assert result.rejection_reason == "BOUNDARY_ARBITRAGE_BOT"


def test_stale_plateau_and_roller_coaster_rejections():
    # Stale Plateau
    stats_plateau = {
        "all_time_pnl_usd": 100000.0,
        "trades_count": 200,
        "active_days": 90.0,
        "trades_per_day": 2.2,
        "win_rate_pct": 80.0,
        "max_drawdown_pct": 10.0,
        "cumulative_pnl": 100000.0,
        "is_stale_plateau": True,
    }
    res_plateau = score_wallet(stats_plateau)
    assert res_plateau.status == "rejected"
    assert res_plateau.rejection_reason == "STALE_PLATEAU_PROFILE"

    # Roller-coaster
    stats_roller = {
        "all_time_pnl_usd": 100000.0,
        "trades_count": 200,
        "active_days": 90.0,
        "trades_per_day": 2.2,
        "win_rate_pct": 80.0,
        "max_drawdown_pct": 10.0,
        "cumulative_pnl": 100000.0,
        "is_roller_coaster": True,
    }
    res_roller = score_wallet(stats_roller)
    assert res_roller.status == "rejected"
    assert res_roller.rejection_reason == "ROLLER_COASTER_GAMBLER_PROFILE"

    # Inconsistent OLS / lumpy profile
    stats_inconsistent = {
        "all_time_pnl_usd": 100000.0,
        "trades_count": 200,
        "active_days": 90.0,
        "trades_per_day": 2.2,
        "win_rate_pct": 80.0,
        "max_drawdown_pct": 10.0,
        "cumulative_pnl": 100000.0,
        "is_inconsistent_profile": True,
    }
    res_inconsistent = score_wallet(stats_inconsistent)
    assert res_inconsistent.status == "rejected"
    assert res_inconsistent.rejection_reason == "INCONSISTENT_LUMPY_PROFILE"


def test_drawdown_and_cumulative_pnl_rejections():
    # Drawdown > 25%
    stats_dd = {
        "all_time_pnl_usd": 100000.0,
        "trades_count": 200,
        "active_days": 90.0,
        "trades_per_day": 2.2,
        "win_rate_pct": 80.0,
        "max_drawdown_pct": 28.5,
        "cumulative_pnl": 100000.0,
    }
    res_dd = score_wallet(stats_dd)
    assert res_dd.status == "rejected"
    assert res_dd.rejection_reason == "DRAWDOWN_TOO_HIGH"

    # Non-positive cumulative reconstructed PnL
    stats_neg_pnl = {
        "all_time_pnl_usd": 100000.0,
        "trades_count": 200,
        "active_days": 90.0,
        "trades_per_day": 2.2,
        "win_rate_pct": 80.0,
        "max_drawdown_pct": 10.0,
        "cumulative_pnl": -500.0,
    }
    res_neg_pnl = score_wallet(stats_neg_pnl)
    assert res_neg_pnl.status == "rejected"
    assert res_neg_pnl.rejection_reason == "RECONSTRUCTED_PNL_NON_POSITIVE"


def test_legitimate_gold_sniper_qualifies():
    stats = {
        "all_time_pnl_usd": 145000.0,
        "total_volume_usd": 350000.0,
        "trades_count": 320,
        "active_days": 75.0,
        "trades_per_day": 4.2,
        "win_rate_pct": 87.5,
        "max_drawdown_pct": 9.5,
        "cumulative_pnl": 145000.0,
        "outlier_concentration_pct": 0.12,
        "unrealized_open_pnl": 500.0,
        "is_inactive_7d": False,
        "is_hft": False,
        "is_conflicting_positions": False,
        "is_boundary_arb": False,
        "is_stale_plateau": False,
        "is_roller_coaster": False,
        "is_inconsistent_profile": False,
        "is_sleeve_incompatible": False,
        "is_wash_trading": False,
    }
    result = score_wallet(stats)
    assert result.status == "active"
    assert result.tier == "gold_sniper"
    assert result.copyability_flag is True


def test_authentic_wallet_stats_calculations():
    now_sec = time.time()
    old_ts = now_sec - (10 * 86400)  # 10 days ago (inactive)

    # Inactive trades
    trades = [
        {"timestamp": old_ts, "price": 0.50, "size": 100, "side": "BUY", "conditionId": "cond1", "asset": "asset1"}
    ]
    stats = calculate_authentic_wallet_stats(
        address="0x123",
        trades=trades,
        positions=[],
        activity=[],
        closed_positions=[]
    )
    assert stats["is_inactive_7d"] is True
    assert stats["days_since_last_trade"] >= 9.9

    # Boundary sniping trade
    boundary_trades = [
        {"timestamp": now_sec, "price": 0.99995, "size": 100, "side": "BUY", "conditionId": "cond2", "asset": "asset2"}
    ]
    stats_bound = calculate_authentic_wallet_stats(
        address="0x123",
        trades=boundary_trades,
        positions=[],
        activity=[],
        closed_positions=[]
    )
    assert stats_bound["is_boundary_arb"] is True

    # Conflicting BUY positions on same market
    conflict_trades = [
        {"timestamp": now_sec, "price": 0.50, "size": 100, "side": "BUY", "conditionId": "mkt1", "outcome": "YES", "asset": "asset_yes"},
        {"timestamp": now_sec + 1, "price": 0.50, "size": 100, "side": "BUY", "conditionId": "mkt1", "outcome": "NO", "asset": "asset_no"},
    ]
    stats_conflict = calculate_authentic_wallet_stats(
        address="0x123",
        trades=conflict_trades,
        positions=[],
        activity=[],
        closed_positions=[]
    )
    assert stats_conflict["is_conflicting_positions"] is True


def test_pure_proportional_sleeve_sizing():
    # Specification:
    # S_w = user_portfolio_balance / n_active
    # f = whale_trade_usd / whale_pnl_or_net_worth
    # copy_order_size = S_w * f

    # 1. $10,000 balance / 10 active whales = $1,000 sleeve.
    # Whale risks 10% ($50,000 / $500,000) -> Copy order size = $1,000 * 0.10 = $100.00
    res1 = calculate_pure_proportional_order_size(
        user_balance=10000.0,
        n_active=10,
        whale_trade_usd=50000.0,
        whale_pnl_or_net_worth=500000.0,
    )
    assert res1.status == "SUCCESS"
    assert res1.value == 100.0

    # 2. Portfolio grows to $20,000. S_w scales to $2,000!
    # Copy order size = $2,000 * 0.10 = $200.00
    res2 = calculate_pure_proportional_order_size(
        user_balance=20000.0,
        n_active=10,
        whale_trade_usd=50000.0,
        whale_pnl_or_net_worth=500000.0,
    )
    assert res2.status == "SUCCESS"
    assert res2.value == 200.0

    # 3. Via size_trade wrapper with pure_proportional=True
    res3 = size_trade(
        user_balance=10000.0,
        risk_profile=None,
        n_active=10,
        whale_trade_value=50000.0,
        whale_portfolio_value=500000.0,
        pure_proportional=True,
    )
    assert res3.status == "SUCCESS"
    assert res3.value == 100.0

    # 4. Available cash limitation constraint
    res_cash_limited = calculate_pure_proportional_order_size(
        user_balance=10000.0,
        n_active=10,
        whale_trade_usd=50000.0,
        whale_pnl_or_net_worth=500000.0,
        available_cash=65.50,
    )
    assert res_cash_limited.status == "SUCCESS"
    assert res_cash_limited.value == 65.50

    # 5. Below minimum order size ($1.00)
    res_tiny = calculate_pure_proportional_order_size(
        user_balance=1000.0,
        n_active=10,
        whale_trade_usd=5.0,
        whale_pnl_or_net_worth=100000.0,  # 100 * (5 / 100000) = 0.005 < 1.0
        min_order_usd=1.0,
    )
    assert res_tiny.status == "SKIPPED_BELOW_MINIMUM"
    assert res_tiny.value == 0.0
