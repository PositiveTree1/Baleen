import pytest
from app.scoring.engine import score_wallet
from app.scoring.basket import compute_baleen_score, select_top_10_roster
from app.models import Wallet

def test_hard_filters_outlier_concentration_25pct():
    """Verifies that single trade profit > 25% of lifetime PnL is rejected."""
    stats_pass = {
        'all_time_pnl_usd': 100000.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.20, # 20% <= 25% passes
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 8.0,
        'trades_count': 150
    }
    assert score_wallet(stats_pass).status == "active"

    stats_fail = {
        'all_time_pnl_usd': 100000.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.28, # 28% > 25% rejected
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 8.0,
        'trades_count': 150
    }
    res_fail = score_wallet(stats_fail)
    assert res_fail.status == "rejected"
    assert res_fail.rejection_reason == "OUTLIER_CONCENTRATION_TOO_HIGH"

def test_mandatory_onchain_history_filter():
    """Verifies that wallets with missing onchain history are rejected."""
    stats_no_history = {
        'all_time_pnl_usd': 80000.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.15,
        'win_rate_pct': 75.0,
        'max_drawdown_pct': 5.0,
        'trades_count': 100,
        'has_no_history': True
    }
    res = score_wallet(stats_no_history)
    assert res.status == "rejected"
    assert res.rejection_reason == "MISSING_ONCHAIN_HISTORY"

def test_5factor_quantitative_baleen_score():
    """Verifies 5-factor scoring components (Sortino, Odds calibration, Breadth, Recency, Copyability)."""
    stats_elite = {
        'all_time_pnl_usd': 500000.0,
        'win_rate_pct': 85.0,
        'max_drawdown_pct': 5.0,
        'trades_count': 200,
        'category_count': 4,
        'avg_entry_price': 0.45,
        'daily_pnl_history': [{'net_pnl': 500.0, 'won_usd': 600.0, 'lost_usd': -100.0}] * 15
    }
    score = compute_baleen_score(stats_elite)
    assert 85.0 <= score <= 100.0

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
        baleen_score=86.0, # 2 points higher, but < 5 pt buffer!
        tier="gold_sniper",
        status="tracked"
    )
    w_challenger_strong = Wallet(
        address="0xCHALLENGER_STRONG",
        name="Strong Challenger",
        baleen_score=92.0, # 8 points higher (> 5 pt buffer!)
        tier="gold_sniper",
        status="tracked"
    )

    roster = select_top_10_roster(
        candidates=[w_incumbent, w_challenger_close, w_challenger_strong],
        current_incumbent_addresses={"0xincumbent"},
        hysteresis_buffer=5.0
    )

    # w_challenger_strong (92) is #1
    # w_incumbent (84 + 5 = 89) beats w_challenger_close (86) and retains slot #2!
    assert roster[0].address == "0xCHALLENGER_STRONG"
    assert roster[1].address == "0xINCUMBENT"
    assert roster[2].address == "0xCHALLENGER_CLOSE"
