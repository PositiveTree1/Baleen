import pytest
from app.discovery.scanner import calculate_authentic_wallet_stats
from app.scoring.engine import score_wallet

def _base_valid_stats(**overrides):
    stats = {
        'all_time_pnl_usd': 100000.0,
        'total_volume_usd': 200000.0,
        'trades_count': 200,
        'active_days': 90.0,
        'avg_trades_per_day': 5.0,
        'outlier_concentration_pct': 0.10,
        'win_rate_pct': 70.0,
        'max_drawdown_pct': 8.0,
        'is_sleeve_incompatible': False,
        'is_wash_trading': False,
        'has_no_history': False,
        'is_boundary_arb': False,
        'is_conflicting_positions': False,
        'is_inconsistent_profile': False,
    }
    stats.update(overrides)
    return stats

def test_filter_13_rejects_conflicting_positions():
    stats = _base_valid_stats(is_conflicting_positions=True)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "CONFLICTING_POSITIONS_DETECTED"
    assert res.copyability_flag is False

def test_filter_13_accepts_clean_directional_positions():
    stats = _base_valid_stats(is_conflicting_positions=False)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None
    assert res.copyability_flag is True

def test_filter_14_rejects_inconsistent_lumpy_profile():
    stats = _base_valid_stats(is_inconsistent_profile=True)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "INCONSISTENT_LUMPY_PROFILE"
    assert res.copyability_flag is False

def test_filter_14_accepts_steady_organic_profile():
    stats = _base_valid_stats(is_inconsistent_profile=False)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None

def test_calculate_authentic_stats_detects_conflicting_positions():
    # Simulate a wallet trading both YES and NO on same condition
    trades = [
        {"conditionId": "0xcond_fed", "side": "BUY", "outcome": "YES", "asset": "tok_yes", "usdcSize": 5000.0, "price": 0.80, "timestamp": 1700000000},
        {"conditionId": "0xcond_fed", "side": "BUY", "outcome": "NO", "asset": "tok_no", "usdcSize": 5000.0, "price": 0.20, "timestamp": 1700001000},
        {"conditionId": "0xcond_cpi", "side": "BUY", "outcome": "YES", "asset": "tok_cpi_yes", "usdcSize": 5000.0, "price": 0.75, "timestamp": 1700002000},
        {"conditionId": "0xcond_cpi", "side": "BUY", "outcome": "NO", "asset": "tok_cpi_no", "usdcSize": 5000.0, "price": 0.25, "timestamp": 1700003000},
    ]
    positions = [
        {"conditionId": "0xcond_fed", "asset": "tok_yes", "outcome": "YES", "size": 6250.0, "avgPrice": 0.80, "closed": False},
        {"conditionId": "0xcond_fed", "asset": "tok_no", "outcome": "NO", "size": 25000.0, "avgPrice": 0.20, "closed": False},
    ]
    stats = calculate_authentic_wallet_stats(
        address="0xhedger",
        positions=positions,
        activity=[],
        profile={"pnl": 120000.0, "volume": 500000.0},
        trades=trades
    )
    assert stats["is_conflicting_positions"] is True
    assert stats["conflicting_ratio"] > 0.50
    assert stats["conflicting_markets_count"] >= 1

def test_calculate_authentic_stats_clean_directional_wallet():
    # Simulate a clean directional trader buying single outcome per condition
    trades = [
        {"conditionId": f"0xcond_{i}", "side": "BUY", "outcome": "YES", "asset": f"tok_{i}", "usdcSize": 500.0, "price": 0.60, "timestamp": 1700000000 + i * 86400}
        for i in range(10)
    ]
    positions = [
        {"conditionId": f"0xcond_{i}", "asset": f"tok_{i}", "outcome": "YES", "size": 833.0, "avgPrice": 0.60, "closed": True, "cashPnl": 333.0, "endDate": f"2026-05-{10+i:02d}"}
        for i in range(10)
    ]
    stats = calculate_authentic_wallet_stats(
        address="0xclean",
        positions=positions,
        activity=[],
        profile={"pnl": 80000.0, "volume": 200000.0},
        trades=trades
    )
    assert stats["is_conflicting_positions"] is False
    assert stats["conflicting_ratio"] == 0.0
    assert stats["conflicting_markets_count"] == 0

def test_pnl_reconstruction_avoids_earliest_date_clustering():
    # Verify that closed positions with explicit endDates do NOT get clustered into min(daily_map.keys())
    trades = [
        {"conditionId": "0xcond_aug", "side": "BUY", "asset": "tok_aug", "size": 100.0, "price": 0.50, "timestamp": 1723939200}, # 2024-08-18
        {"conditionId": "0xcond_aug", "side": "SELL", "asset": "tok_aug", "size": 100.0, "price": 0.60, "timestamp": 1723939300}, # 2024-08-18 (+10 PnL)
    ]
    positions = [
        # Position closed in March
        {
            "conditionId": "0xcond_march",
            "asset": "tok_march",
            "size": 0.0,
            "avgPrice": 0.40,
            "curPrice": 1.0,
            "closed": True,
            "cashPnl": 5000.0,
            "endDate": "2024-03-15T12:00:00Z"
        },
        # Position closed in May
        {
            "conditionId": "0xcond_may",
            "asset": "tok_may",
            "size": 0.0,
            "avgPrice": 0.35,
            "curPrice": 1.0,
            "closed": True,
            "cashPnl": 6000.0,
            "endDate": "2024-05-20T12:00:00Z"
        }
    ]
    stats = calculate_authentic_wallet_stats(
        address="0xsteady",
        positions=positions,
        activity=[],
        profile={"pnl": 11010.0, "volume": 50000.0},
        trades=trades
    )
    daily_hist = stats["daily_pnl_history"]
    dates = [d["date"] for d in daily_hist]
    
    # Crucial check: March and May must have their own distinct dates, NOT clustered onto 2024-08-18!
    assert "2024-03-15" in dates
    assert "2024-05-20" in dates
    assert "2024-08-18" in dates

    # Verify PnL on 2024-08-18 is only the Aug trade (+10), not a giant $11k lump!
    aug_entry = next(d for d in daily_hist if d["date"] == "2024-08-18")
    assert aug_entry["net_pnl"] == 10.0

def test_lumpy_profile_detection():
    # If 90% of profit occurs in 1 single day, is_inconsistent_profile should trigger
    history_trades = []
    positions = []
    # Day 1: +$50,000 jump
    positions.append({
        "conditionId": "0xcond_big",
        "asset": "tok_big",
        "size": 0.0,
        "avgPrice": 0.20,
        "curPrice": 1.0,
        "closed": True,
        "cashPnl": 50000.0,
        "endDate": "2026-08-01"
    })
    # Days 2-10: tiny $50 wins
    for i in range(2, 10):
        positions.append({
            "conditionId": f"0xcond_{i}",
            "asset": f"tok_{i}",
            "size": 0.0,
            "avgPrice": 0.50,
            "curPrice": 1.0,
            "closed": True,
            "cashPnl": 50.0,
            "endDate": f"2026-08-{i:02d}"
        })
    stats = calculate_authentic_wallet_stats(
        address="0xlumpy",
        positions=positions,
        activity=[],
        profile={"pnl": 50400.0, "volume": 100000.0},
        trades=[]
    )
    assert stats["is_inconsistent_profile"] is True
    assert stats["max_single_day_pnl_ratio"] > 0.80

def test_closed_positions_parameter_reconstructs_multi_month_trajectory():
    # Simulates historical closed positions from January through April with authentic timestamps
    closed_positions = [
        {
            "conditionId": "0xcond_jan",
            "asset": "tok_jan",
            "realizedPnl": 15000.0,
            "avgPrice": 0.40,
            "totalBought": 25000.0,
            "curPrice": 1.0,
            "timestamp": 1769640728,  # 2026-01-28
            "outcome": "Yes",
            "title": "Fed interest rate decision Jan"
        },
        {
            "conditionId": "0xcond_feb",
            "asset": "tok_feb",
            "realizedPnl": 12000.0,
            "avgPrice": 0.45,
            "totalBought": 20000.0,
            "curPrice": 1.0,
            "timestamp": 1772000000,  # 2026-02-25
            "outcome": "Yes",
            "title": "Super Bowl winner"
        },
        {
            "conditionId": "0xcond_mar",
            "asset": "tok_mar",
            "realizedPnl": 8000.0,
            "avgPrice": 0.50,
            "totalBought": 16000.0,
            "curPrice": 1.0,
            "timestamp": 1774500000,  # 2026-03-25
            "outcome": "Yes",
            "title": "Academy Awards Best Picture"
        }
    ]
    # Recent trades in August
    trades = [
        {"conditionId": "0xcond_aug", "side": "BUY", "asset": "tok_aug", "size": 100.0, "price": 0.50, "timestamp": 1723939200},
        {"conditionId": "0xcond_aug", "side": "SELL", "asset": "tok_aug", "size": 100.0, "price": 0.60, "timestamp": 1723939300}
    ]

    stats = calculate_authentic_wallet_stats(
        address="0xsteady_whale",
        positions=[],
        activity=[],
        profile={"pnl": 35010.0, "volume": 100000.0},
        trades=trades,
        closed_positions=closed_positions
    )

    daily = stats["daily_pnl_history"]
    dates = [d["date"] for d in daily]

    # Verify that multi-month dates are properly reconstructed
    assert any(d.startswith("2026-01") for d in dates)
    assert any(d.startswith("2026-02") for d in dates)
    assert any(d.startswith("2026-03") for d in dates)
    assert stats["win_rate_pct"] == 100.0
    assert stats["all_time_pnl_usd"] == 35010.0
    assert stats["is_inconsistent_profile"] is False

def test_conflicting_positions_up_down_markets():
    # Simulates a wallet trading both UP and DOWN on the same condition
    trades = [
        {"conditionId": "0xcond_btc_5m", "side": "BUY", "outcome": "UP", "asset": "tok_up", "usdcSize": 2000.0, "price": 0.70, "timestamp": 1700000000},
        {"conditionId": "0xcond_btc_5m", "side": "BUY", "outcome": "DOWN", "asset": "tok_down", "usdcSize": 2000.0, "price": 0.30, "timestamp": 1700001000}
    ]
    stats = calculate_authentic_wallet_stats(
        address="0xupdown_hedger",
        positions=[],
        activity=[],
        trades=trades
    )
    assert stats["is_conflicting_positions"] is True
    assert stats["conflicting_markets_count"] == 1

def test_conflicting_positions_open_loss_hedging_trap():
    # Simulates the exact trap described by the user:
    # A trader holding opposing Yes/No positions with >$10k unrealized paper losses
    positions = [
        {
            "conditionId": "0xcond_fed_meeting",
            "asset": "tok_yes",
            "outcome": "YES",
            "size": 50000.0,
            "avgPrice": 0.85,
            "curPrice": 0.10,
            "cashPnl": -37500.0,
            "closed": False
        },
        {
            "conditionId": "0xcond_fed_meeting",
            "asset": "tok_no",
            "outcome": "NO",
            "size": 50000.0,
            "avgPrice": 0.79,
            "curPrice": 0.05,
            "cashPnl": -37000.0,
            "closed": False
        },
        {
            "conditionId": "0xcond_cpi_meeting",
            "asset": "tok_cpi_yes",
            "outcome": "YES",
            "size": 20000.0,
            "avgPrice": 0.80,
            "curPrice": 0.10,
            "cashPnl": -14000.0,
            "closed": False
        },
        {
            "conditionId": "0xcond_cpi_meeting",
            "asset": "tok_cpi_no",
            "outcome": "NO",
            "size": 20000.0,
            "avgPrice": 0.80,
            "curPrice": 0.10,
            "cashPnl": -14000.0,
            "closed": False
        }
    ]
    stats = calculate_authentic_wallet_stats(
        address="0xhemorrhaging_hedger",
        positions=positions,
        activity=[],
        profile={"pnl": 121000.0, "volume": 500000.0},
        trades=[]
    )
    assert stats["is_conflicting_positions"] is True
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "CONFLICTING_POSITIONS_DETECTED"
