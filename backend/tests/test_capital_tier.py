import pytest
from app.sizing.capital_tier import (
    get_target_wallet_count,
    calculate_min_capital_required,
    filter_active_wallets_by_capital
)
from app.discovery.scanner import calculate_authentic_wallet_stats

def test_capital_tiered_wallet_counts():
    # Below $250: Follow 1 top sniper
    assert get_target_wallet_count(50.0) == 1
    assert get_target_wallet_count(100.0) == 1
    assert get_target_wallet_count(249.99) == 1

    # $250 - $999: Follow 2 top snipers
    assert get_target_wallet_count(250.0) == 2
    assert get_target_wallet_count(500.0) == 2
    assert get_target_wallet_count(999.0) == 2

    # $1,000 - $2,999: Follow 4 snipers
    assert get_target_wallet_count(1000.0) == 4
    assert get_target_wallet_count(2500.0) == 4

    # $3,000 - $4,999: Follow 6 snipers
    assert get_target_wallet_count(3000.0) == 6
    assert get_target_wallet_count(4500.0) == 6

    # $5,000+: Follow 10 snipers
    assert get_target_wallet_count(5000.0) == 10
    assert get_target_wallet_count(25000.0) == 10

def test_calculate_min_capital_required():
    # Whale with $100k net worth and $1k median trade (f = 0.01) -> min capital = $100
    assert calculate_min_capital_required(100000.0, 1000.0, 1.0) == 100.0
    # Whale with $500k net worth and $250 median trade (f = 0.0005) -> min capital clamped to $1,000
    assert calculate_min_capital_required(500000.0, 250.0, 1.0) == 1000.0
    # Whale with high fraction (f = 0.1) -> min capital clamped to $50 min
    assert calculate_min_capital_required(10000.0, 1000.0, 1.0) == 50.0

def test_filter_active_wallets_by_capital():
    dummy_wallets = [f"wallet_{i}" for i in range(10)]
    # At $100, only the #1 wallet is selected
    assert filter_active_wallets_by_capital(dummy_wallets, 100.0) == ["wallet_0"]
    # At $500, top 2 wallets
    assert filter_active_wallets_by_capital(dummy_wallets, 500.0) == ["wallet_0", "wallet_1"]
    # At $10,000, all 10
    assert len(filter_active_wallets_by_capital(dummy_wallets, 10000.0)) == 10

def test_win_rate_anomaly_guardrail():
    # Simulate an API returning 20 winning positions and 0 losses for a wallet with $50k profile PnL
    # Gross wins = 20 * $5,000 = $100,000, but all_time_pnl is only $50,000
    fake_closed = [
        {"asset": f"0x{i}", "conditionId": f"0xc{i}", "cashPnl": 5000.0, "realizedPnl": 5000.0}
        for i in range(20)
    ]
    profile = {"pnl": 50000.0}
    stats = calculate_authentic_wallet_stats("0xtest", [], [], profile, [], fake_closed)
    
    # The anomaly guardrail must NOT report 100% win rate!
    assert stats["win_rate_pct"] < 100.0
    assert stats["win_rate_pct"] > 0.0

def test_cumulative_curve_calibration_guardrail():
    # If daily history sums up to $200k, but profile is $50k, curve must be calibrated to $50k
    fake_closed = [
        {"asset": f"0x{i}", "conditionId": f"0xc{i}", "cashPnl": 10000.0, "realizedPnl": 10000.0, "timestamp": 1770000000 + i * 86400}
        for i in range(20)
    ]
    profile = {"pnl": 50000.0}
    stats = calculate_authentic_wallet_stats("0xtest2", [], [], profile, [], fake_closed)
    
    # Final cumulative PnL must match the authoritative profile PnL
    assert stats["cumulative_pnl"] == 50000.0

def test_capital_tier_applies_gates_13_and_14():
    """Spec v2 Part D: Capital tier roster applies Gates 13 & 14 within the tier."""
    from app.models import Wallet

    # At $1,500 capital, target count is 4 wallets
    # Max category concentration = max(1, int(4 * 0.40)) = 1 per category!
    w0 = Wallet(address="0xw0", baleen_score=95.0, tier="gold_sniper", status="active")
    w1 = Wallet(address="0xw1", baleen_score=94.0, tier="gold_sniper", status="active")
    w2 = Wallet(address="0xw2", baleen_score=93.0, tier="standard", status="active")
    w4 = Wallet(address="0xw4", baleen_score=88.0, tier="standard", status="active")
    w5 = Wallet(address="0xw5", baleen_score=85.0, tier="standard", status="active")
    w6 = Wallet(address="0xw6", baleen_score=82.0, tier="standard", status="active")

    categories = {
        "0xw0": "Crypto",
        "0xw1": "Crypto",  # Correlated and same category
        "0xw2": "Crypto",  # Exceeds 40% category cap
        "0xw4": "Sports",
        "0xw5": "Politics",
        "0xw6": "Macro",
    }

    # w0 and w1 have identical daily PnL (correlation ~1.0)
    hist_corr = [{"date": f"2026-08-{i:02d}", "daily_pnl": float(i * 100)} for i in range(1, 10)]
    hist_uncorr = [{"date": f"2026-08-{i:02d}", "daily_pnl": float((10 - i) * 50 if i % 2 == 0 else -30)} for i in range(1, 10)]

    histories = {
        "0xw0": hist_corr,
        "0xw1": hist_corr,
        "0xw2": hist_uncorr,
        "0xw4": hist_uncorr,
        "0xw5": hist_uncorr,
        "0xw6": hist_uncorr,
    }

    candidates = [w0, w1, w2, w4, w5, w6]
    tier_roster = filter_active_wallets_by_capital(
        wallets=candidates,
        capital_usd=1500.0,
        wallet_histories=histories,
        wallet_categories=categories
    )

    assert len(tier_roster) == 4
    roster_addrs = [w.address for w in tier_roster]
    assert roster_addrs == ["0xw0", "0xw4", "0xw5", "0xw6"]

