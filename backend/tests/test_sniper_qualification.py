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
    # Conflicting BUY positions using outcomeIndex
    conflict_trades_idx = [
        {"timestamp": now_sec, "price": 0.50, "size": 100, "side": "BUY", "conditionId": "mkt2", "outcomeIndex": 0, "asset": "asset_0"},
        {"timestamp": now_sec + 1, "price": 0.50, "size": 100, "side": "BUY", "conditionId": "mkt2", "outcomeIndex": 1, "asset": "asset_1"},
    ]
    stats_conflict_idx = calculate_authentic_wallet_stats(
        address="0x123",
        trades=conflict_trades_idx,
        positions=[],
        activity=[],
        closed_positions=[]
    )
    assert stats_conflict_idx["is_conflicting_positions"] is True

    # Empty trade history should be flagged inactive
    stats_empty = calculate_authentic_wallet_stats(
        address="0xempty",
        trades=[],
        positions=[],
        activity=[],
        closed_positions=[]
    )
    assert stats_empty["is_inactive_7d"] is True
    assert stats_empty["days_since_last_trade"] == 999.0


def test_trade_count_100_and_120_accepted():
    # Exactly 100 lifetime trades passes
    stats_100 = {
        "all_time_pnl_usd": 80000.0,
        "total_volume_usd": 250000.0,
        "trades_count": 100,
        "active_days": 65.0,
        "trades_per_day": 1.5,
        "win_rate_pct": 75.0,
        "max_drawdown_pct": 10.0,
        "cumulative_pnl": 80000.0,
    }
    res_100 = score_wallet(stats_100)
    assert res_100.status == "active"

    # 120 lifetime trades (which prior attempt failed because of leftover < 150 check)
    stats_120 = {
        "all_time_pnl_usd": 80000.0,
        "total_volume_usd": 250000.0,
        "trades_count": 120,
        "active_days": 65.0,
        "trades_per_day": 1.8,
        "win_rate_pct": 75.0,
        "max_drawdown_pct": 10.0,
        "cumulative_pnl": 80000.0,
    }
    res_120 = score_wallet(stats_120)
    assert res_120.status == "active"


def test_stale_plateau_negative_second_half():
    # Whale made money in first half but lost money in second half
    trades = [
        {"timestamp": 1700000000, "price": 0.40, "size": 100, "side": "BUY", "conditionId": "c1", "asset": "a1"},
        {"timestamp": 1700000050, "price": 0.80, "size": 100, "side": "SELL", "conditionId": "c1", "asset": "a1"},
        {"timestamp": 1700100000, "price": 0.50, "size": 100, "side": "BUY", "conditionId": "c2", "asset": "a2"},
        {"timestamp": 1700100050, "price": 0.10, "size": 100, "side": "SELL", "conditionId": "c2", "asset": "a2"},
    ]
    stats = calculate_authentic_wallet_stats(
        address="0xstale",
        trades=trades,
        positions=[],
        activity=[],
        closed_positions=[]
    )
    assert stats["is_stale_plateau"] is True


def test_gold_sniper_ols_slope_and_r2():
    # 5-day history with poor R^2 (< 0.55) fails gold sniper tier (falls back to standard)
    stats_poor_r2 = {
        "all_time_pnl_usd": 150000.0,
        "total_volume_usd": 400000.0,
        "trades_count": 200,
        "active_days": 70.0,
        "trades_per_day": 2.8,
        "win_rate_pct": 88.0,
        "max_drawdown_pct": 8.0,
        "cumulative_pnl": 150000.0,
        "unrealized_open_pnl": 0.0,
        "t_days": 6,
        "beta": 100.0,
        "r_squared": 0.48,  # < 0.55
    }
    res_poor = score_wallet(stats_poor_r2)
    assert res_poor.status == "active"
    assert res_poor.tier == "standard"

    # 5-day history with solid R^2 (>= 0.55) qualifies for gold sniper
    stats_good_r2 = {
        "all_time_pnl_usd": 150000.0,
        "total_volume_usd": 400000.0,
        "trades_count": 200,
        "active_days": 70.0,
        "trades_per_day": 2.8,
        "win_rate_pct": 88.0,
        "max_drawdown_pct": 8.0,
        "cumulative_pnl": 150000.0,
        "unrealized_open_pnl": 0.0,
        "t_days": 6,
        "beta": 150.0,
        "r_squared": 0.82,  # >= 0.55
    }
    res_good = score_wallet(stats_good_r2)
    assert res_good.status == "active"
    assert res_good.tier == "gold_sniper"


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


def test_rejection_reason_hashable():
    from app.scoring.engine import RejectionReason
    r1 = RejectionReason("PNL_BELOW_50K")
    r2 = RejectionReason("INSUFFICIENT_TRADES_UNDER_100")
    # Must be hashable for sets and dictionary keys
    s = {r1, r2}
    assert r1 in s
    assert len(s) == 2
    d = {r1: "reject_pnl", r2: "reject_trades"}
    assert d[r1] == "reject_pnl"


def test_score_wallet_resilient_to_none_values():
    # Dictionary with explicit None values for numeric keys
    stats_with_nones = {
        "all_time_pnl_usd": 120000.0,
        "total_volume_usd": None,
        "trades_count": 200,
        "active_days": None,
        "trades_per_day": 2.5,
        "avg_trades_per_day": None,
        "win_rate_pct": 82.0,
        "max_drawdown_pct": 9.0,
        "cumulative_pnl": 120000.0,
        "unrealized_open_pnl": None,
        "t_days": None,
        "beta": None,
        "r_squared": None,
    }
    result = score_wallet(stats_with_nones)
    assert result.status == "active"
    assert result.tier in ["standard", "gold_sniper"]


@pytest.mark.asyncio
async def test_live_poller_executes_live_orders_for_live_active_links():
    from app.database import SessionLocal, init_db
    from app.models import User, LiveWalletLink, Wallet, ExecutionLog
    from app.services.live_poller import LiveTradeMirrorService
    from sqlalchemy import select, delete

    await init_db()
    whale_addr = "0x" + "a" * 40
    user_email = "poller_live_test@baleen.ai"
    cond_id = "0xcondLivePollerTest"

    async with SessionLocal() as db:
        # Clean prior state
        await db.execute(delete(ExecutionLog).where(ExecutionLog.market_condition_id == cond_id))
        await db.execute(delete(Wallet).where(Wallet.address == whale_addr))
        stmt_u = select(User).where(User.email == user_email)
        u_old = (await db.execute(stmt_u)).scalar_one_or_none()
        if u_old:
            await db.execute(delete(LiveWalletLink).where(LiveWalletLink.user_id == u_old.id))
            await db.execute(delete(User).where(User.id == u_old.id))
        await db.commit()

        # Add active whale
        whale = Wallet(
            address=whale_addr,
            status="active",
            tier="gold_sniper",
            all_time_pnl_usd=250000.0,
            win_rate_pct=88.0,
            avg_trades_per_day=3.0,
            is_hft=False,
            dormant=False
        )
        db.add(whale)

        # Add live-enabled user with active link
        u = User(
            email=user_email,
            password_hash="pwd",
            sandbox_balance_usd=10000.0,
            live_trading_enabled=True
        )
        db.add(u)
        await db.flush()

        link = LiveWalletLink(
            user_id=u.id,
            provider="polymarket_clob",
            provider_user_id="0xproxyUser",
            polymarket_wallet_address="0xproxyUser000000000000000000000000000000",
            clob_api_key_enc="key123",
            clob_api_secret_enc="sec123",
            clob_api_passphrase_enc="pass123",
            is_live_active=True,
            live_balance_usdc=5000.0,
            last_verified_at=datetime.utcnow()
        )
        db.add(link)
        await db.commit()

    service = LiveTradeMirrorService()

    # Process BUY fill
    await service.process_trade_fill(
        wallet_address=whale_addr,
        condition_id=cond_id,
        title="Will Baleen L2 Live Mirror Succeed?",
        side="BUY",
        price=0.50,
        cash_usd=5000.0,
        dt=datetime.utcnow(),
        outcome="Yes",
        asset="0xassetLive1"
    )

    async with SessionLocal() as db:
        # Check that BOTH sandbox and live execution logs were created
        stmt_sandbox = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cond_id,
            ExecutionLog.is_sandbox == True
        )
        sandbox_logs = (await db.execute(stmt_sandbox)).scalars().all()
        assert len(sandbox_logs) >= 1

        stmt_live = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cond_id,
            ExecutionLog.is_sandbox == False
        )
        live_logs = (await db.execute(stmt_live)).scalars().all()
        assert len(live_logs) >= 1
        live_entry = live_logs[0]
        assert live_entry.side == "BUY"
        assert live_entry.status == "FILLED"
        assert live_entry.notional_usd > 0.0

        # Live balance should have been decremented
        stmt_link_check = select(LiveWalletLink).where(LiveWalletLink.user_id == u.id)
        updated_link = (await db.execute(stmt_link_check)).scalar_one()
        assert updated_link.live_balance_usdc < 5000.0

    # Process SELL fill
    await service.process_trade_fill(
        wallet_address=whale_addr,
        condition_id=cond_id,
        title="Will Baleen L2 Live Mirror Succeed?",
        side="SELL",
        price=0.80,  # Profitable exit
        cash_usd=5000.0,
        dt=datetime.utcnow(),
        outcome="Yes",
        asset="0xassetLive1"
    )

    async with SessionLocal() as db:
        stmt_live_sell = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cond_id,
            ExecutionLog.is_sandbox == False,
            ExecutionLog.side == "SELL"
        )
        live_sells = (await db.execute(stmt_live_sell)).scalars().all()
        assert len(live_sells) >= 1
        assert live_sells[0].status == "CLOSED"
        assert live_sells[0].realized_pnl_usd is not None
        assert live_sells[0].realized_pnl_usd > 0  # Sold at 0.80 vs bought at 0.50

        # Clean test records
        await db.execute(delete(ExecutionLog).where(ExecutionLog.market_condition_id == cond_id))
        await db.execute(delete(LiveWalletLink).where(LiveWalletLink.user_id == u.id))
        await db.execute(delete(User).where(User.id == u.id))
        await db.execute(delete(Wallet).where(Wallet.address == whale_addr))
        await db.commit()


# =========================================================================
# Spec v2 Dedicated Tests: Gates 8, 10, 11, 12, 13, 14
# =========================================================================

def test_spec_v2_gate_8_tiered_boundary_bands():
    """Gate 8: Tiered volume bands replace single cliff."""
    now_ts = time.time()
    
    # Breach Band 1: Volume at 0.98 is 10% (> 5% max allowed)
    trades_band1 = [
        {"timestamp": now_ts - i * 3600, "price": 0.50, "size": 90, "side": "BUY", "usdcSize": 90.0, "conditionId": "c1"}
        for i in range(10)
    ] + [
        {"timestamp": now_ts - 500, "price": 0.98, "size": 100, "side": "BUY", "usdcSize": 100.0, "conditionId": "c2"}
    ]
    # Total buy volume: 90*10 + 100 = 1000. 100/1000 = 10% > 5%
    stats1 = calculate_authentic_wallet_stats("0xb1", trades=trades_band1, positions=[], activity=[], closed_positions=[])
    assert stats1["is_boundary_arb"] is True

    # Breach Band 2: Volume at 0.92 is 25% (> 20% max allowed)
    trades_band2 = [
        {"timestamp": now_ts - i * 3600, "price": 0.50, "size": 75, "side": "BUY", "usdcSize": 75.0, "conditionId": "c1"}
        for i in range(10)
    ] + [
        {"timestamp": now_ts - 500, "price": 0.92, "size": 250, "side": "BUY", "usdcSize": 250.0, "conditionId": "c2"}
    ]
    # Total buy volume: 750 + 250 = 1000. 250/1000 = 25% > 20%
    stats2 = calculate_authentic_wallet_stats("0xb2", trades=trades_band2, positions=[], activity=[], closed_positions=[])
    assert stats2["is_boundary_arb"] is True

    # Breach Band 3: Volume at 0.85 is 45% (> 40% max allowed)
    trades_band3 = [
        {"timestamp": now_ts - i * 3600, "price": 0.50, "size": 55, "side": "BUY", "usdcSize": 55.0, "conditionId": "c1"}
        for i in range(10)
    ] + [
        {"timestamp": now_ts - 500, "price": 0.85, "size": 450, "side": "BUY", "usdcSize": 450.0, "conditionId": "c2"}
    ]
    # Total buy volume: 550 + 450 = 1000. 450/1000 = 45% > 40%
    stats3 = calculate_authentic_wallet_stats("0xb3", trades=trades_band3, positions=[], activity=[], closed_positions=[])
    assert stats3["is_boundary_arb"] is True

    # Clean trader within all 3 bands (2% Band 1, 10% Band 2, 20% Band 3)
    trades_clean = [
        {"timestamp": now_ts - i * 3600, "price": 0.50, "size": 100, "side": "BUY", "usdcSize": 100.0, "conditionId": "c1"}
        for i in range(10)
    ] + [
        {"timestamp": now_ts - 100, "price": 0.98, "size": 20, "side": "BUY", "usdcSize": 20.0, "conditionId": "c2"},
        {"timestamp": now_ts - 200, "price": 0.92, "size": 80, "side": "BUY", "usdcSize": 80.0, "conditionId": "c3"},
        {"timestamp": now_ts - 300, "price": 0.85, "size": 100, "side": "BUY", "usdcSize": 100.0, "conditionId": "c4"}
    ]
    # Total buy: 1000 + 20 + 80 + 100 = 1200.
    # Band 1: 20/1200 = 1.6% <= 5%
    # Band 2: (20+80)/1200 = 8.3% <= 20%
    # Band 3: (20+80+100)/1200 = 16.7% <= 40%
    stats_clean = calculate_authentic_wallet_stats("0xb_clean", trades=trades_clean, positions=[], activity=[], closed_positions=[])
    assert stats_clean["is_boundary_arb"] is False


def test_spec_v2_gate_10_anti_stale_plateau():
    """Gate 10: Trailing 90-day realized PnL must be >= 35% of total lifetime PnL."""
    from datetime import datetime, timedelta
    
    # 1. Stale plateau: Total $100k, but only $10k in trailing 90 days (10% < 35%)
    now_dt = datetime.utcnow()
    d_old = (now_dt - timedelta(days=120)).strftime("%Y-%m-%d")
    d_recent = (now_dt - timedelta(days=20)).strftime("%Y-%m-%d")
    
    history_stale = [
        {"date": d_old, "daily_pnl": 90000.0},
        {"date": d_recent, "daily_pnl": 10000.0},
    ]
    stats_stale = calculate_authentic_wallet_stats(
        "0xstale90",
        trades=[{"timestamp": time.time(), "side": "BUY", "price": 0.50, "size": 100}],
        positions=[],
        activity=[],
        profile={"pnl": 100000.0, "volume": 300000.0},
        closed_positions=[{"date": d_old, "cashPnl": 90000.0, "realizedPnl": 90000.0, "closed": True}]
    )
    # Inject 90d history test
    stats_stale_explicit = dict(stats_stale)
    stats_stale_explicit["daily_pnl_history"] = history_stale
    res_stale = calculate_authentic_wallet_stats(
        "0xstale90",
        trades=[{"timestamp": time.time(), "side": "BUY", "price": 0.50, "size": 100}],
        positions=[],
        activity=[],
        profile={"pnl": 100000.0, "volume": 300000.0},
        closed_positions=[
            {"conditionId": "c_old", "timestamp": (now_dt - timedelta(days=120)).timestamp(), "cashPnl": 90000.0, "realizedPnl": 90000.0, "closed": True},
            {"conditionId": "c_rec", "timestamp": (now_dt - timedelta(days=20)).timestamp(), "cashPnl": 10000.0, "realizedPnl": 10000.0, "closed": True}
        ]
    )
    assert res_stale["is_stale_plateau"] is True

    # 2. Active Alpha: Total $100k, with $50k in trailing 90 days (50% >= 35%)
    res_active = calculate_authentic_wallet_stats(
        "0xactive90",
        trades=[{"timestamp": time.time(), "side": "BUY", "price": 0.50, "size": 100}],
        positions=[],
        activity=[],
        profile={"pnl": 100000.0, "volume": 300000.0},
        closed_positions=[
            {"conditionId": "c_old2", "timestamp": (now_dt - timedelta(days=120)).timestamp(), "cashPnl": 50000.0, "realizedPnl": 50000.0, "closed": True},
            {"conditionId": "c_rec2", "timestamp": (now_dt - timedelta(days=20)).timestamp(), "cashPnl": 50000.0, "realizedPnl": 50000.0, "closed": True}
        ]
    )
    assert res_active["is_stale_plateau"] is False


def test_spec_v2_gate_11_period_sharpe():
    """Gate 11: Trailing-90-day Sharpe ratio on period returns > 1.0."""
    now_dt = datetime.utcnow()
    from datetime import timedelta
    
    # Highly volatile / erratic trader (Sharpe <= 1.0)
    erratic_closed = [
        {"conditionId": f"c_err_{i}", "timestamp": (now_dt - timedelta(days=i * 5)).timestamp(), "cashPnl": 1000.0 if i % 2 == 0 else -950.0, "realizedPnl": 1000.0 if i % 2 == 0 else -950.0, "closed": True}
        for i in range(15)
    ]
    stats_erratic = calculate_authentic_wallet_stats(
        "0xerratic",
        trades=[{"timestamp": time.time(), "side": "BUY", "price": 0.50, "size": 100}],
        positions=[],
        activity=[],
        profile={"pnl": 100000.0, "volume": 300000.0},
        closed_positions=erratic_closed
    )
    assert stats_erratic["trailing_90d_sharpe"] < 1.0
    assert stats_erratic["is_inconsistent_profile"] is True

    # Steady alpha trader (Sharpe > 1.0)
    steady_closed = [
        {"conditionId": f"c_std_{i}", "timestamp": (now_dt - timedelta(days=i * 5)).timestamp(), "cashPnl": 500.0 + (i * 10), "realizedPnl": 500.0 + (i * 10), "closed": True}
        for i in range(15)
    ]
    stats_steady = calculate_authentic_wallet_stats(
        "0xsteady",
        trades=[{"timestamp": time.time(), "side": "BUY", "price": 0.50, "size": 100}],
        positions=[],
        activity=[],
        profile={"pnl": 10000.0, "volume": 50000.0},
        closed_positions=steady_closed
    )
    assert stats_steady["trailing_90d_sharpe"] > 1.0
    assert stats_steady["is_inconsistent_profile"] is False


def test_spec_v2_gate_13_category_concentration_cap():
    """Gate 13: Max 40% of the active roster from the same category."""
    from app.scoring.basket import select_top_10_roster
    from app.models import Wallet

    # Create 10 candidates: 6 Crypto, 2 Sports, 2 Politics
    candidates = []
    categories = {}
    for i in range(6):
        addr = f"0xCrypto_{i}"
        w = Wallet(address=addr, baleen_score=95.0 - i, tier="standard", status="tracked")
        candidates.append(w)
        categories[addr.lower()] = "Crypto"

    for i in range(2):
        addr = f"0xSports_{i}"
        w = Wallet(address=addr, baleen_score=85.0 - i, tier="standard", status="tracked")
        candidates.append(w)
        categories[addr.lower()] = "Sports"

    for i in range(2):
        addr = f"0xPolitics_{i}"
        w = Wallet(address=addr, baleen_score=80.0 - i, tier="standard", status="tracked")
        candidates.append(w)
        categories[addr.lower()] = "Politics"

    # In a 10-wallet roster, 40% of 10 = max 4 per category
    roster = select_top_10_roster(
        candidates=candidates,
        target_size=10,
        wallet_categories=categories
    )

    crypto_in_roster = sum(1 for w in roster if categories.get(w.address.lower()) == "Crypto")
    sports_in_roster = sum(1 for w in roster if categories.get(w.address.lower()) == "Sports")
    politics_in_roster = sum(1 for w in roster if categories.get(w.address.lower()) == "Politics")

    # Only 4 Crypto wallets allowed (despite 6 having higher raw scores than Sports/Politics)
    assert crypto_in_roster == 4
    assert sports_in_roster == 2
    assert politics_in_roster == 2
    assert len(roster) == 8  # 4 + 2 + 2 = 8 available unique diversified wallets


def test_spec_v2_gate_14_pairwise_correlation_filter():
    """Gate 14: Daily PnL correlation r <= 0.70 between candidates."""
    from app.scoring.basket import select_top_10_roster, compute_daily_pnl_correlation
    from app.models import Wallet

    # Candidate A and Candidate B trade identical markets with 0.99 correlation
    hist_a = [{"date": f"2026-08-{i:02d}", "daily_pnl": float(i * 100)} for i in range(1, 15)]
    hist_b = [{"date": f"2026-08-{i:02d}", "daily_pnl": float(i * 98 + 5)} for i in range(1, 15)]
    # Candidate C is uncorrelated
    hist_c = [{"date": f"2026-08-{i:02d}", "daily_pnl": float((15 - i) * 80 if i % 2 == 0 else -50)} for i in range(1, 15)]

    r_ab = compute_daily_pnl_correlation(hist_a, hist_b)
    r_ac = compute_daily_pnl_correlation(hist_a, hist_c)
    assert r_ab > 0.95  # Strongly correlated
    assert r_ac < 0.20  # Uncorrelated

    w_a = Wallet(address="0xCandidateA", baleen_score=92.0, tier="gold_sniper", status="tracked")
    w_b = Wallet(address="0xCandidateB", baleen_score=90.0, tier="gold_sniper", status="tracked")
    w_c = Wallet(address="0xCandidateC", baleen_score=85.0, tier="standard", status="tracked")

    histories = {
        "0xcandidatea": hist_a,
        "0xcandidateb": hist_b,
        "0xcandidatec": hist_c,
    }

    # Selecting top 2: w_a is rank 1, w_b is rank 2 but correlated with w_a (r > 0.70)
    # Gate 14 skips w_b and selects w_c instead!
    roster = select_top_10_roster(
        candidates=[w_a, w_b, w_c],
        target_size=2,
        wallet_histories=histories
    )

    assert len(roster) == 2
    assert roster[0].address == "0xCandidateA"
    assert roster[1].address == "0xCandidateC"  # B skipped due to correlation!


