import pytest
from app.scoring.engine import score_wallet
from app.scoring.basket import compute_baleen_score, select_top_10_roster, normalize_and_score_pool
from app.models import Wallet

def test_hard_filters_outlier_concentration_25pct():
    """Verifies that single trade profit > 25% of lifetime PnL is rejected."""
    stats_pass = {
        'all_time_pnl_usd': 100000.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.20,
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 8.0,
        'trades_count': 150,
        'active_days': 60.0
    }
    assert score_wallet(stats_pass).status == "active"

    stats_fail = {
        'all_time_pnl_usd': 100000.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.28,
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 8.0,
        'trades_count': 150,
        'active_days': 60.0
    }
    res_fail = score_wallet(stats_fail)
    assert res_fail.status == "rejected"
    assert res_fail.rejection_reason == "OUTLIER_CONCENTRATION_TOO_HIGH"

def test_anti_hft_maker_bot_filter():
    """Verifies that bots with > 15 trades/day are rejected."""
    stats_hft = {
        'all_time_pnl_usd': 100000.0,
        'avg_trades_per_day': 18.0, # > 15 trades/day
        'outlier_concentration_pct': 0.10,
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 5.0,
        'trades_count': 300,
        'active_days': 60.0
    }
    res = score_wallet(stats_hft)
    assert res.status == "rejected"
    assert res.rejection_reason == "HFT_MAKER_BOT_EXCEEDED"

def test_sleeve_compatibility_and_wash_trading_filters():
    """Verifies sleeve size compatibility and wash-trading flags."""
    # Incompatible sleeve size (<$20 or >$3,000)
    stats_bad_size = {
        'all_time_pnl_usd': 100000.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.10,
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 5.0,
        'trades_count': 200,
        'is_sleeve_incompatible': True
    }
    res_sz = score_wallet(stats_bad_size)
    assert res_sz.status == "rejected"
    assert res_sz.rejection_reason == "SLEEVE_SIZE_INCOMPATIBLE"

    # Wash trading bot
    stats_wash = {
        'all_time_pnl_usd': 100000.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.10,
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 5.0,
        'trades_count': 200,
        'is_wash_trading': True
    }
    res_w = score_wallet(stats_wash)
    assert res_w.status == "rejected"
    assert res_w.rejection_reason == "WASH_TRADING_PATTERN"

def test_intra_pool_dynamic_normalization():
    """Verifies that 5-factor scoring min-max normalizes metrics across candidate pool."""
    wallet_a = {
        'win_rate_pct': 60.0,
        'avg_entry_price': 0.40, # +20% edge
        'all_time_pnl_usd': 200000.0,
        'category_count': 4,
        'median_trade_size': 100.0,
        'daily_pnl_history': [{'daily_pnl': 200.0}] * 10
    }
    wallet_b = {
        'win_rate_pct': 80.0,
        'avg_entry_price': 0.78, # +2% edge
        'all_time_pnl_usd': 60000.0,
        'category_count': 1,
        'median_trade_size': 500.0,
        'daily_pnl_history': [{'daily_pnl': 50.0}] * 10
    }

    scores = normalize_and_score_pool([wallet_a, wallet_b])
    assert len(scores) == 2
    # Wallet A has superior edge and breadth -> outscores B
    assert scores[0] > scores[1]

def test_roster_5pt_hysteresis_prevents_churn():
    """
    Verifies that an incumbent active wallet is protected by a +5.0 point buffer,
    so a challenger on the bench with +2 points DOES NOT displace it.
    """
    w_incumbent = Wallet(
        address="0xINCUMBENT",
        name="Incumbent Whale",
        baleen_score=84.0,
        tier="gold_sniper",
        status="active"
    )
    w_challenger_close = Wallet(
        address="0xCHALLENGER_CLOSE",
        name="Close Challenger",
        baleen_score=86.0,
        tier="gold_sniper",
        status="tracked"
    )
    w_challenger_strong = Wallet(
        address="0xCHALLENGER_STRONG",
        name="Strong Challenger",
        baleen_score=92.0,
        tier="gold_sniper",
        status="tracked"
    )

    roster = select_top_10_roster(
        candidates=[w_incumbent, w_challenger_close, w_challenger_strong],
        current_incumbent_addresses={"0xincumbent"},
        hysteresis_buffer=5.0
    )

    assert roster[0].address == "0xCHALLENGER_STRONG"
    assert roster[1].address == "0xINCUMBENT"
    assert roster[2].address == "0xCHALLENGER_CLOSE"
