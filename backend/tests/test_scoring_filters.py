from app.scoring.engine import score_wallet

def test_pnl_threshold_rejects_below_50k(make_wallet_stats):
    stats = make_wallet_stats(pnl=49000.0)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "PNL_BELOW_THRESHOLD"

def test_hft_screen_rejects_over_100_trades_per_day(make_wallet_stats):
    stats = make_wallet_stats(trades_per_day=101.0)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "HFT_EXCEEDED"

def test_outlier_concentration_rejects_single_trade_over_35pct(make_wallet_stats):
    stats = make_wallet_stats(outlier_pct=0.36)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "OUTLIER_CONCENTRATION_TOO_HIGH"

def test_gold_tier_requires_both_winrate_and_drawdown(make_wallet_stats):
    # High win rate, bad drawdown
    stats = make_wallet_stats(win_rate=90.0, max_drawdown=15.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.tier.lower() == "standard"
    
    # Good drawdown, low win rate
    stats2 = make_wallet_stats(win_rate=80.0, max_drawdown=5.0)
    res2 = score_wallet(stats2)
    assert res2.status == "active"
    assert res2.tier.lower() == "standard"

def test_gold_tier_accepts_qualifying_wallet(make_wallet_stats):
    stats = make_wallet_stats(win_rate=86.0, max_drawdown=9.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.tier.lower() in ["gold_sniper", "gold sniper"]

def test_wallet_above_all_thresholds_but_failing_drawdown(make_wallet_stats):
    stats = make_wallet_stats(win_rate=90.0, max_drawdown=11.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.tier.lower() == "standard"

def test_boundary_arbitrage_filter_rejects_boundary_snipers(make_wallet_stats):
    stats = make_wallet_stats(is_boundary_arb=True)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "ARBITRAGE_BOUNDARY_SNIPER"
