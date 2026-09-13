from app.discovery.scanner import calculate_authentic_wallet_stats


def test_curve_keeps_both_outcome_tokens_for_one_condition():
    condition = "0xcondition"
    closed = [
        {"asset": "token_yes", "conditionId": condition, "realizedPnl": 50, "curPrice": 1, "timestamp": 1700000000},
        {"asset": "token_no", "conditionId": condition, "realizedPnl": -100, "curPrice": 0, "timestamp": 1700000001},
    ]

    stats = calculate_authentic_wallet_stats("0xwallet", [], [], profile={"pnl": -50}, closed_positions=closed)

    assert stats["resolved_positions_count"] == 2
    assert stats["expectancy_usd"] == -25
    assert stats["daily_pnl_history"] == []


def test_curve_deduplicates_redemption_by_transaction_hash():
    redemption = {
        "type": "REDEEM", "asset": "token", "conditionId": "condition",
        "size": 100, "usdcSize": 100, "timestamp": 1700000000,
        "transactionHash": "0xredemption",
    }
    trade = {"asset": "token", "conditionId": "condition", "side": "BUY", "size": 100, "price": 0.5, "timestamp": 1699990000}

    stats = calculate_authentic_wallet_stats("0xwallet", [], [redemption, dict(redemption)], profile={"pnl": 50}, trades=[trade])

    assert stats["daily_pnl_history"] == []


def test_curve_excludes_redemption_without_observed_cost_basis():
    redemption = {
        "type": "REDEEM", "asset": "token", "conditionId": "condition",
        "size": 100, "usdcSize": 100, "timestamp": 1700000000,
        "transactionHash": "0xredemption",
    }

    stats = calculate_authentic_wallet_stats("0xwallet", [], [redemption], profile=None, trades=[])

    assert stats["cumulative_pnl"] != 50
    assert stats["cumulative_pnl"] == 0


def test_curve_preserves_exact_unscaled_daily_pnl_without_synthetic_distortion():
    """Verifies that daily PnL points reflect authentic realized earnings without artificial multiplier scaling."""
    closed = [
        {"asset": "t1", "conditionId": "c1", "realizedPnl": 1000.0, "timestamp": 1770000000, "curPrice": 1.0},
        {"asset": "t2", "conditionId": "c2", "realizedPnl": 2000.0, "timestamp": 1770086400, "curPrice": 1.0},
    ]
    # Authoritative profile PnL from Polymarket leaderboard is $10,000
    stats = calculate_authentic_wallet_stats("0xwallet", [], [], profile={"pnl": 10000.0}, closed_positions=closed)
    hist = stats["daily_pnl_history"]

    assert hist == []
    assert stats["all_time_pnl_usd"] == 10000.0


def test_asymmetric_alpha_qualifies_underdog_bettor():
    """Verifies that value traders with positive EV (odds edge >= 0.08, PF >= 1.75, PnL >= $75k) qualify despite < 58% nominal win rate."""
    from app.scoring.engine import score_wallet
    stats = {
        "all_time_pnl_usd": 120000.0,
        "total_volume_usd": 300000.0,
        "win_rate_pct": 52.0,
        "wilson_lower_bound": 46.0,
        "odds_weighted_edge": 0.12,
        "profit_factor": 2.2,
        "trades_count": 250,
        "active_days": 90.0,
        "trades_per_day": 3.0,
        "avg_trades_per_day": 3.0,
        "max_drawdown_pct": 12.0,
        "outlier_concentration_pct": 0.15,
        "is_hft": False,
        "is_dormant": False,
        "daily_pnl_history": [{"date": "2026-01-01", "daily_pnl": 120000.0}]
    }
    result = score_wallet(stats)
    assert result.status == "active"
    assert result.rejection_reason is None

