import pytest
from unittest.mock import AsyncMock, MagicMock
from app.scoring.engine import score_wallet
from app.discovery.scanner import evaluate_pending_wallets
from app.database import SessionLocal, init_db
from app.models import Wallet
from sqlalchemy import select, delete


def _valid_stats(**overrides) -> dict:
    """Helper to generate a base valid wallet stats dictionary passing all gatekeeper filters."""
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
    }
    stats.update(overrides)
    return stats


# -------------------------------------------------------------------------
# Filter 1: Minimum Realized PnL ($50k) and Minimum Traded Volume ($150k)
# -------------------------------------------------------------------------

def test_pnl_threshold_rejects_below_50k():
    stats = _valid_stats(all_time_pnl_usd=49999.0)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "PNL_BELOW_THRESHOLD"


def test_pnl_threshold_accepts_at_50k():
    stats = _valid_stats(all_time_pnl_usd=50000.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None


def test_volume_filter_rejects_149999():
    stats = _valid_stats(all_time_pnl_usd=100000.0, total_volume_usd=149999.0)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "VOLUME_BELOW_THRESHOLD"


def test_volume_filter_accepts_150000():
    stats = _valid_stats(all_time_pnl_usd=100000.0, total_volume_usd=150000.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None


def test_volume_filter_high_pnl_exemption():
    # Volume < $150k is exempted if realized PnL >= $250k
    stats = _valid_stats(all_time_pnl_usd=250000.0, total_volume_usd=100000.0)
    res = score_wallet(stats)
    assert res.status == "active"


# -------------------------------------------------------------------------
# Filter 2: Track Record Length (>= 150 trades and >= 60 active days)
# -------------------------------------------------------------------------

def test_trade_count_gate_rejects_zero_trades():
    stats = _valid_stats(all_time_pnl_usd=100000.0, trades_count=0)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "INSUFFICIENT_TRACK_RECORD_TRADES"


def test_trade_count_gate_rejects_149_trades_below_500k_pnl():
    stats = _valid_stats(all_time_pnl_usd=499999.0, trades_count=149)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "INSUFFICIENT_TRACK_RECORD_TRADES"


def test_trade_count_gate_accepts_150_trades_below_500k_pnl():
    stats = _valid_stats(all_time_pnl_usd=100000.0, trades_count=150)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None


def test_trade_count_gate_high_pnl_exemption():
    # Trade count < 150 is exempted if realized PnL >= $500k
    stats = _valid_stats(all_time_pnl_usd=500000.0, trades_count=1)
    res = score_wallet(stats)
    assert res.status == "active"


def test_active_days_gate_rejects_59_days_below_500k_pnl():
    stats = _valid_stats(all_time_pnl_usd=100000.0, active_days=59.0)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "INSUFFICIENT_ACTIVE_HISTORY_DAYS"


def test_active_days_gate_accepts_60_days_below_500k_pnl():
    stats = _valid_stats(all_time_pnl_usd=100000.0, active_days=60.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None


def test_active_days_gate_high_pnl_exemption():
    # Active days < 60 is exempted if realized PnL >= $500k
    stats = _valid_stats(all_time_pnl_usd=500000.0, active_days=10.0)
    res = score_wallet(stats)
    assert res.status == "active"


# -------------------------------------------------------------------------
# Filter 3: Anti-HFT / Maker-Rebate (<= 15 trades/day)
# -------------------------------------------------------------------------

def test_hft_screen_rejects_over_15_trades_per_day():
    stats = _valid_stats(avg_trades_per_day=15.1)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "HFT_MAKER_BOT_EXCEEDED"


def test_hft_screen_accepts_15_trades_per_day():
    stats = _valid_stats(avg_trades_per_day=15.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None


# -------------------------------------------------------------------------
# Filter 4: Closed Position Concentration Cap (<= 25% of positive realized PnL)
# -------------------------------------------------------------------------

def test_outlier_concentration_rejects_over_25pct():
    stats = _valid_stats(outlier_concentration_pct=0.251)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "OUTLIER_CONCENTRATION_TOO_HIGH"


def test_outlier_concentration_accepts_25pct():
    stats = _valid_stats(outlier_concentration_pct=0.25)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None


# -------------------------------------------------------------------------
# Filter 5: Sleeve Size Compatibility ($20 <= median trade <= $3,000)
# -------------------------------------------------------------------------

def test_sleeve_size_compatibility_filter():
    stats_bad = _valid_stats(is_sleeve_incompatible=True)
    res_bad = score_wallet(stats_bad)
    assert res_bad.status == "rejected"
    assert res_bad.rejection_reason == "SLEEVE_SIZE_INCOMPATIBLE"

    stats_good = _valid_stats(is_sleeve_incompatible=False)
    res_good = score_wallet(stats_good)
    assert res_good.status == "active"


# -------------------------------------------------------------------------
# Filter 6: Wash-Trading Detection (<120s BUY<->SELL pairs <= 10%)
# -------------------------------------------------------------------------

def test_wash_trading_filter():
    stats_wash = _valid_stats(is_wash_trading=True)
    res_wash = score_wallet(stats_wash)
    assert res_wash.status == "rejected"
    assert res_wash.rejection_reason == "WASH_TRADING_PATTERN"

    stats_clean = _valid_stats(is_wash_trading=False)
    res_clean = score_wallet(stats_clean)
    assert res_clean.status == "active"


# -------------------------------------------------------------------------
# Filter 7: Mandatory On-Chain History Requirement
# -------------------------------------------------------------------------

def test_missing_onchain_history_filter():
    stats_no_hist = _valid_stats(has_no_history=True)
    res_no_hist = score_wallet(stats_no_hist)
    assert res_no_hist.status == "rejected"
    assert res_no_hist.rejection_reason == "MISSING_ONCHAIN_HISTORY"


# -------------------------------------------------------------------------
# Filter 8: Boundary Arbitrage Bot Filter (0.01 / 0.99 snipers)
# -------------------------------------------------------------------------

def test_boundary_arbitrage_filter_rejects_boundary_snipers():
    stats = _valid_stats(is_boundary_arb=True)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "ARBITRAGE_BOUNDARY_SNIPER"


# -------------------------------------------------------------------------
# Filter 9: Minimum Win Rate (>= 55.0%)
# -------------------------------------------------------------------------

def test_win_rate_gate_rejects_54_9pct():
    stats = _valid_stats(win_rate_pct=54.9)
    res = score_wallet(stats)
    assert res.status == "rejected"
    assert res.rejection_reason == "WIN_RATE_TOO_LOW"


def test_win_rate_gate_accepts_55_0pct():
    stats = _valid_stats(win_rate_pct=55.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.rejection_reason is None


# -------------------------------------------------------------------------
# Tier Classification: Gold Sniper vs Standard
# -------------------------------------------------------------------------

def test_gold_tier_requires_both_winrate_and_drawdown():
    # High win rate, bad drawdown (>12.0%)
    stats1 = _valid_stats(win_rate_pct=90.0, max_drawdown_pct=18.0)
    res1 = score_wallet(stats1)
    assert res1.status == "active"
    assert res1.tier == "standard"

    # Good drawdown, low win rate (<80.0%)
    stats2 = _valid_stats(win_rate_pct=75.0, max_drawdown_pct=5.0)
    res2 = score_wallet(stats2)
    assert res2.status == "active"
    assert res2.tier == "standard"


def test_gold_tier_accepts_qualifying_wallet():
    # Win rate >= 80.0% and Max Drawdown <= 12.0%
    stats = _valid_stats(win_rate_pct=80.0, max_drawdown_pct=12.0)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.tier == "gold_sniper"


def test_wallet_above_all_thresholds_but_failing_drawdown():
    stats = _valid_stats(win_rate_pct=90.0, max_drawdown_pct=12.1)
    res = score_wallet(stats)
    assert res.status == "active"
    assert res.tier == "standard"


# -------------------------------------------------------------------------
# Scanner Integration: Deep Evaluation & Baleen Score Assignment
# -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_evaluate_pending_wallets_computes_baleen_score():
    await init_db()
    test_addr = "0x1111222233334444555566667777888899990000"

    async with SessionLocal() as db:
        # Clean existing test records
        await db.execute(delete(Wallet).where(Wallet.address == test_addr))
        pending_wallet = Wallet(
            address=test_addr,
            status="pending",
            tier="pending"
        )
        db.add(pending_wallet)
        await db.commit()

    # Mock PolymarketClient with authentic-shaped data
    mock_client = MagicMock()
    mock_client.fetch_wallet_positions = AsyncMock(return_value=[
        {
            "conditionId": f"0xcond_{i}",
            "title": f"Will Event {i} Resolve YES?",
            "size": 1000.0,
            "currentValue": 500.0,
            "avgPrice": 0.40,
            "curPrice": 0.50,
            "cashPnl": 10000.0,
            "percentPnl": 25.0,
            "realizedPnl": 10000.0,
            "unrealizedPnl": 0.0,
            "closed": True,
            "timestamp": 1700000000 + i * 86400 * 10
        }
        for i in range(10)
    ])
    mock_client.fetch_wallet_activity = AsyncMock(return_value=[
        {
            "type": "TRADE",
            "timestamp": 1700000000 + i * 86400,
            "usdcSize": 250.0,
            "side": "BUY",
            "conditionId": f"0xcond_{i % 5}"
        }
        for i in range(160)
    ])
    mock_client.fetch_wallet_profile = AsyncMock(return_value={
        "pnl": 100000.0,
        "volume": 300000.0,
        "userName": "TopWhale",
        "pseudonym": "AlphaSniper",
        "profileImage": "https://example.com/avatar.png"
    })
    mock_client.fetch_wallet_trades = AsyncMock(return_value=[
        {
            "id": f"t_{i}",
            "timestamp": 1700000000 + i * 86400,
            "usdcSize": 250.0,
            "price": 0.45,
            "side": "BUY",
            "conditionId": f"0xcond_{i % 5}"
        }
        for i in range(160)
    ])
    mock_client.close = AsyncMock()

    try:
        async with SessionLocal() as db:
            await evaluate_pending_wallets(db, mock_client)
            await db.commit()

        async with SessionLocal() as db:
            wallet = (await db.execute(select(Wallet).where(Wallet.address == test_addr))).scalar_one_or_none()
            assert wallet is not None
            assert wallet.status == "active"
            assert wallet.baleen_score is not None
            assert isinstance(wallet.baleen_score, float)
            assert wallet.baleen_score >= 0.0
            assert wallet.tier in ["standard", "gold_sniper"]
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(Wallet).where(Wallet.address == test_addr))
            await db.commit()
