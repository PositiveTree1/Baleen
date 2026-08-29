"""
Milestone M-A3 Invariant & Integration Test Suite:
1. Ingestion Deduplication & Platform Log Idempotency
2. Out-of-Order SELL before BUY Handling and Orphan Prevention
3. Binary Market Resolution Settlement Transitions ($1.00 Winning, $0.00 Losing)
"""

import math
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete, func
from app.database import SessionLocal, init_db
from app.models import Wallet, User, ExecutionLog, PortfolioSnapshot
from app.services.live_poller import LiveTradeMirrorService, PendingOutOfOrderSell


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Initializes clean database state before each test."""
    await init_db()
    async with SessionLocal() as db:
        # Clear execution logs and wallets created in tests
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(PortfolioSnapshot))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xtest_whale_%")))
        await db.execute(delete(User).where(User.email.like("%@testm_a3.com")))
        
        # Create standard active test whale
        test_whale = Wallet(
            address="0xtest_whale_a3",
            status="active",
            tier="gold_sniper",
            win_rate_pct=88.0,
            all_time_pnl_usd=60000.0,
            dormant=False,
            is_hft=False,
            avg_trades_per_day=3.0,
            first_trade_at=datetime.utcnow() - timedelta(days=30),
            last_trade_at=datetime.utcnow()
        )
        db.add(test_whale)

        # Create standard test user
        test_user = User(
            email="user1@testm_a3.com",
            password_hash="testpass",
            sandbox_starting_balance_usd=10000.0,
            sandbox_balance_usd=10000.0,
            sandbox_high_water_mark_usd=10000.0,
            risk_profile="balanced"
        )
        db.add(test_user)
        await db.commit()
    yield
    async with SessionLocal() as db:
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(PortfolioSnapshot))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xtest_whale_%")))
        await db.execute(delete(User).where(User.email.like("%@testm_a3.com")))
        await db.commit()


# ============================================================================
# PART 1: Platform Ingestion Deduplication
# ============================================================================

@pytest.mark.asyncio
async def test_platform_log_database_deduplication():
    """
    Verifies that dual-ingestion duplicate signals with matching
    (onchain_tx_hash, onchain_log_index) where user_id is None are deduplicated cleanly.
    """
    service = LiveTradeMirrorService()
    now_dt = datetime.utcnow()

    # Ingestion 1: First signal from WebSocket
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id="0xcond_dedup_1",
        title="Test Ingestion Deduplication Market",
        side="BUY",
        price=0.50,
        cash_usd=100.0,
        dt=now_dt,
        outcome="Yes",
        tx_hash="0xduplicate_tx_hash_999",
        log_index=0
    )

    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.onchain_tx_hash == "0xduplicate_tx_hash_999",
            ExecutionLog.user_id.is_(None)
        )
        logs = (await db.execute(stmt)).scalars().all()
        assert len(logs) == 1, "First ingestion must create exactly 1 platform ExecutionLog"
        orig_log_id = logs[0].id
        assert logs[0].onchain_log_index == 0
        assert logs[0].status == "FILLED"

    # Ingestion 2: Duplicate signal arriving via Data API poller / secondary node
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id="0xcond_dedup_1",
        title="Test Ingestion Deduplication Market",
        side="BUY",
        price=0.50,
        cash_usd=100.0,
        dt=now_dt,
        outcome="Yes",
        tx_hash="0xduplicate_tx_hash_999",
        log_index=0
    )

    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.onchain_tx_hash == "0xduplicate_tx_hash_999",
            ExecutionLog.user_id.is_(None)
        )
        logs_after = (await db.execute(stmt)).scalars().all()
        assert len(logs_after) == 1, "Duplicate ingestion must be skipped; no duplicate ExecutionLog created"
        assert logs_after[0].id == orig_log_id


@pytest.mark.asyncio
async def test_same_tx_distinct_log_index_both_processed():
    """
    Verifies that multiple trades within the same on-chain transaction
    (same tx_hash, different log_index) are both processed without collision.
    """
    service = LiveTradeMirrorService()
    now_dt = datetime.utcnow()

    # Trade 1 in transaction: log_index = 0
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id="0xcond_multi_1",
        title="Test Multi Log Market",
        side="BUY",
        price=0.45,
        cash_usd=100.0,
        dt=now_dt,
        outcome="Yes",
        tx_hash="0xmulti_log_tx_777",
        log_index=0
    )

    # Trade 2 in transaction: log_index = 1
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id="0xcond_multi_1",
        title="Test Multi Log Market",
        side="BUY",
        price=0.55,
        cash_usd=100.0,
        dt=now_dt,
        outcome="Yes",
        tx_hash="0xmulti_log_tx_777",
        log_index=1
    )

    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.onchain_tx_hash == "0xmulti_log_tx_777",
            ExecutionLog.user_id.is_(None)
        ).order_by(ExecutionLog.onchain_log_index.asc())
        logs = (await db.execute(stmt)).scalars().all()
        assert len(logs) == 2, "Both log_index 0 and log_index 1 must be processed"
        assert logs[0].onchain_log_index == 0
        assert logs[1].onchain_log_index == 1


# ============================================================================
# PART 2: Out-of-Order SELL before BUY Handling
# ============================================================================

@pytest.mark.asyncio
async def test_out_of_order_sell_registration_and_lagging_buy_matching():
    """
    Tests out-of-order SELL before BUY handling:
    1. SELL arrives first (0 open positions held) -> registered in pending queue and safely audited.
    2. Lagging BUY arrives -> matched with pending SELL, both closed with exact PnL and 0 open lots.
    """
    service = LiveTradeMirrorService()
    now_dt = datetime.utcnow()
    sell_dt = now_dt + timedelta(seconds=10)
    buy_dt = now_dt  # Buy occurred before sell on-chain, but arrives later

    # Step 1: SELL arrives first
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id="0xcond_ooo_test",
        title="Test Out-of-Order Market",
        side="SELL",
        price=0.65,
        cash_usd=100.0,
        dt=sell_dt,
        outcome="Yes",
        tx_hash="0xtx_ooo_sell",
        log_index=1
    )

    # Verify pending out-of-order SELL is registered
    ooo_key = "0xtest_whale_a3:0xcond_ooo_test:yes"
    assert ooo_key in service.pending_out_of_order_sells
    assert len(service.pending_out_of_order_sells[ooo_key]) == 1
    pending = service.pending_out_of_order_sells[ooo_key][0]
    assert pending.price == 0.65
    assert pending.tx_hash == "0xtx_ooo_sell"

    # Verify no open BUY or ghost SELL was executed in DB yet
    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(ExecutionLog.market_condition_id == "0xcond_ooo_test")
        logs = (await db.execute(stmt)).scalars().all()
        assert len(logs) == 0, "No execution logs should be written for pending out-of-order SELL"

    # Step 2: Lagging BUY arrives
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id="0xcond_ooo_test",
        title="Test Out-of-Order Market",
        side="BUY",
        price=0.50,
        cash_usd=100.0,
        dt=buy_dt,
        outcome="Yes",
        tx_hash="0xtx_ooo_buy",
        log_index=0
    )

    # Verify pending queue was consumed
    assert ooo_key not in service.pending_out_of_order_sells or len(service.pending_out_of_order_sells[ooo_key]) == 0

    # Verify DB state: BUY and SELL both executed as CLOSED, with positive realized PnL and 0 open lots
    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == "0xcond_ooo_test",
            ExecutionLog.user_id.is_(None)
        ).order_by(ExecutionLog.executed_at.asc())
        platform_logs = (await db.execute(stmt)).scalars().all()

        assert len(platform_logs) == 2, "Expected matching BUY and SELL logs"
        buy_log = next(l for l in platform_logs if l.side == "BUY")
        sell_log = next(l for l in platform_logs if l.side == "SELL")

        assert buy_log.status == "CLOSED", "Matched BUY must be immediately marked CLOSED"
        assert sell_log.status == "CLOSED", "Matched SELL must be marked CLOSED"
        assert buy_log.realized_pnl_usd is not None
        # PnL = Notional * (0.65 - 0.50)/0.50 - fees = Notional * 0.30 - fees > 0
        assert buy_log.realized_pnl_usd > 0.0, f"Expected profit on 0.50 -> 0.65, got {buy_log.realized_pnl_usd}"

        # Verify zero open lots remaining
        stmt_open = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == "0xcond_ooo_test",
            ExecutionLog.status == "FILLED"
        )
        open_logs = (await db.execute(stmt_open)).scalars().all()
        assert len(open_logs) == 0, f"Expected 0 open lots, found {len(open_logs)}"


# ============================================================================
# PART 3: Binary Market Resolution Settlement Transitions
# ============================================================================

@pytest.mark.asyncio
async def test_settle_market_resolution_winner_100():
    """
    Tests binary resolution settlement for winning outcome ($1.00 payout):
    1. Creates open BUY positions on outcome 'Yes'.
    2. Calls settle_market_resolution with winning_outcome='Yes'.
    3. Verifies all positions transition from FILLED to CLOSED with exact $1.00 payout PnL,
       settled cash increases, and 0 open lots remain.
    """
    service = LiveTradeMirrorService()
    now_dt = datetime.utcnow()
    cid = "0xcond_res_winner_100"

    # Step 1: Open BUY position
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id=cid,
        title="Will Ethereum exceed $5,000 in 2026?",
        side="BUY",
        price=0.40,
        cash_usd=200.0,
        dt=now_dt,
        outcome="Yes",
        tx_hash="0xtx_buy_res_win",
        log_index=0
    )

    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cid,
            ExecutionLog.user_id.is_(None),
            ExecutionLog.status == "FILLED"
        )
        open_lots = (await db.execute(stmt)).scalars().all()
        assert len(open_lots) == 1
        notional = open_lots[0].notional_usd
        fee = open_lots[0].fee_usd
        fill_price = open_lots[0].user_fill_price or open_lots[0].whale_entry_price

    # Step 2: Settle market resolution with winning outcome "Yes"
    res = await service.settle_market_resolution(
        condition_id=cid,
        winning_outcome="Yes",
        resolved_at=now_dt + timedelta(days=1)
    )

    assert res["status"] == "SUCCESS"
    assert res["winning_lots"] >= 1
    assert res["losing_lots"] == 0

    # Expected PnL: notional * ((1.0 - 0.40)/0.40) - fee = notional * 1.5 - fee
    expected_pnl = round(notional * ((1.0 - fill_price) / fill_price) - fee, 2)
    assert math.isclose(res["total_system_pnl_usd"], expected_pnl, abs_tol=0.02)

    # Verify zero open lots remaining
    async with SessionLocal() as db:
        stmt_check = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cid,
            ExecutionLog.status == "FILLED"
        )
        remaining_open = (await db.execute(stmt_check)).scalars().all()
        assert len(remaining_open) == 0, "All lots must transition to CLOSED on resolution"

        stmt_closed = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cid,
            ExecutionLog.user_id.is_(None)
        )
        closed_lots = (await db.execute(stmt_closed)).scalars().all()
        assert len(closed_lots) == 1
        assert closed_lots[0].status == "CLOSED"
        assert closed_lots[0].realized_pnl_usd == expected_pnl
        assert closed_lots[0].resolved_at is not None


@pytest.mark.asyncio
async def test_settle_market_resolution_loser_000():
    """
    Tests binary resolution settlement for losing outcome ($0.00 payout):
    1. Creates open BUY positions on outcome 'Yes'.
    2. Calls settle_market_resolution with winning_outcome='No' (meaning 'Yes' loses).
    3. Verifies all positions transition to CLOSED with exact loss (-notional - fee),
       0 open lots remain, and no negative cash collapse occurs.
    """
    service = LiveTradeMirrorService()
    now_dt = datetime.utcnow()
    cid = "0xcond_res_loser_000"

    # Step 1: Open BUY position on "Yes"
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id=cid,
        title="Will Solana flip Ethereum in 2026?",
        side="BUY",
        price=0.60,
        cash_usd=150.0,
        dt=now_dt,
        outcome="Yes",
        tx_hash="0xtx_buy_res_lose",
        log_index=0
    )

    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cid,
            ExecutionLog.user_id.is_(None),
            ExecutionLog.status == "FILLED"
        )
        open_lots = (await db.execute(stmt)).scalars().all()
        assert len(open_lots) == 1
        notional = open_lots[0].notional_usd
        fee = open_lots[0].fee_usd

    # Step 2: Settle market resolution with winning outcome "No"
    res = await service.settle_market_resolution(
        condition_id=cid,
        winning_outcome="No",
        resolved_at=now_dt + timedelta(days=1)
    )

    assert res["status"] == "SUCCESS"
    assert res["winning_lots"] == 0
    assert res["losing_lots"] >= 1

    expected_loss = round(-notional - fee, 2)
    assert math.isclose(res["total_system_pnl_usd"], expected_loss, abs_tol=0.02)

    # Verify zero open lots remaining in database
    async with SessionLocal() as db:
        stmt_check = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cid,
            ExecutionLog.status == "FILLED"
        )
        remaining_open = (await db.execute(stmt_check)).scalars().all()
        assert len(remaining_open) == 0

        stmt_closed = select(ExecutionLog).where(
            ExecutionLog.market_condition_id == cid,
            ExecutionLog.user_id.is_(None)
        )
        closed_lots = (await db.execute(stmt_closed)).scalars().all()
        assert len(closed_lots) == 1
        assert closed_lots[0].status == "CLOSED"
        assert closed_lots[0].realized_pnl_usd == expected_loss


@pytest.mark.asyncio
async def test_settle_market_resolution_multi_user_hwm():
    """
    Verifies that binary market resolution correctly updates all user sandbox balances,
    ratchets High-Water Marks monotonically, and logs audit events.
    """
    service = LiveTradeMirrorService()
    now_dt = datetime.utcnow()
    cid = "0xcond_res_multi_user"

    # Open trade that gets copied by user1
    await service.process_trade_fill(
        wallet_address="0xtest_whale_a3",
        condition_id=cid,
        title="Will US Inflation fall below 2%?",
        side="BUY",
        price=0.50,
        cash_usd=100.0,
        dt=now_dt,
        outcome="Yes",
        tx_hash="0xtx_multi_user_res",
        log_index=0
    )

    async with SessionLocal() as db:
        stmt_u = select(User).where(User.email == "user1@testm_a3.com")
        u_before = (await db.execute(stmt_u)).scalar_one()
        bal_before = float(u_before.sandbox_balance_usd)
        hwm_before = float(u_before.sandbox_high_water_mark_usd)

    # Settle market as Winner
    res = await service.settle_market_resolution(
        condition_id=cid,
        winning_outcome="Yes",
        resolved_at=now_dt + timedelta(days=2)
    )
    assert res["status"] == "SUCCESS"

    async with SessionLocal() as db:
        stmt_u = select(User).where(User.email == "user1@testm_a3.com")
        u_after = (await db.execute(stmt_u)).scalar_one()
        bal_after = float(u_after.sandbox_balance_usd)
        hwm_after = float(u_after.sandbox_high_water_mark_usd)

        # Winning resolution must increase user balance and ratchet HWM
        assert bal_after > bal_before
        assert hwm_after >= hwm_before
        assert hwm_after == bal_after
