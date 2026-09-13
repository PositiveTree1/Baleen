from app.discovery.scanner import calculate_authentic_wallet_stats


def test_curve_keeps_both_outcome_tokens_for_one_condition():
    condition = "0xcondition"
    closed = [
        {"asset": "token_yes", "conditionId": condition, "realizedPnl": 50, "curPrice": 1, "timestamp": 1700000000},
        {"asset": "token_no", "conditionId": condition, "realizedPnl": -100, "curPrice": 0, "timestamp": 1700000001},
    ]

    stats = calculate_authentic_wallet_stats("0xwallet", [], [], profile={"pnl": -50}, closed_positions=closed)

    assert stats["cumulative_pnl"] == -50


def test_curve_deduplicates_redemption_by_transaction_hash():
    redemption = {
        "type": "REDEEM", "asset": "token", "conditionId": "condition",
        "size": 100, "usdcSize": 100, "timestamp": 1700000000,
        "transactionHash": "0xredemption",
    }
    trade = {"asset": "token", "conditionId": "condition", "side": "BUY", "size": 100, "price": 0.5, "timestamp": 1699990000}

    stats = calculate_authentic_wallet_stats("0xwallet", [], [redemption, dict(redemption)], profile={"pnl": 50}, trades=[trade])

    assert stats["cumulative_pnl"] == 50


def test_curve_excludes_redemption_without_observed_cost_basis():
    redemption = {
        "type": "REDEEM", "asset": "token", "conditionId": "condition",
        "size": 100, "usdcSize": 100, "timestamp": 1700000000,
        "transactionHash": "0xredemption",
    }

    stats = calculate_authentic_wallet_stats("0xwallet", [], [redemption], profile=None, trades=[])

    assert stats["cumulative_pnl"] != 50
    assert stats["cumulative_pnl"] == 0
