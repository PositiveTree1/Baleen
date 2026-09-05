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

