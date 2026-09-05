import pytest
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from app.database import SessionLocal, init_db
from app.models import PortfolioSnapshot, ExecutionLog, Wallet, User
from app.api.execution_logs import get_portfolio_snapshots
from app.api.wallets import get_copied_wallet_stats
from app.services.mark_to_market import _last_known_pnl, set_live_price
from app.services.live_poller import LiveTradeMirrorService

@pytest.fixture(autouse=True)
async def clean_state():
    await init_db()
    async with SessionLocal() as db:
        await db.execute(delete(PortfolioSnapshot))
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xr4_%")))
        await db.execute(delete(User).where(User.email.like("r4user%")))
        await db.commit()
    yield
    async with SessionLocal() as db:
        await db.execute(delete(PortfolioSnapshot))
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xr4_%")))
        await db.execute(delete(User).where(User.email.like("r4user%")))
        await db.commit()

@pytest.mark.asyncio
async def test_bug1_portfolio_snapshots_no_premature_truncation():
    """
    Bug 1 Verification:
    Ensure that when table has many snapshots (e.g. 1000 snapshots over 4 days),
    querying snapshots does NOT truncate at limit=500 on the first day,
    but instead returns a continuous timeline covering all days (Sept 2 to Sept 5).
    """
    now = datetime.utcnow()
    start_dt = now - timedelta(days=4)

    async with SessionLocal() as db:
        # Create snapshots spanning 4 days (one every 5 minutes = 1152 snapshots)
        for i in range(1000):
            snap_time = start_dt + timedelta(minutes=i * 5)
            bal = 10000.0 + (i * 2.5) # Balance increasing over time
            db.add(PortfolioSnapshot(
                user_id=None,
                timestamp=snap_time,
                balance=bal,
                total_pnl=bal - 10000.0,
                active_trades_count=5
            ))
        await db.commit()

    async with SessionLocal() as db:
        # Request with limit=100
        snaps = await get_portfolio_snapshots(timeframe="all", limit=100, db=db)
        
        assert len(snaps) <= 100
        assert len(snaps) >= 10
        
        # Earliest returned point should be from day 0
        first_ts = datetime.fromisoformat(snaps[0]["timestamp"].replace("Z", ""))
        last_ts = datetime.fromisoformat(snaps[-1]["timestamp"].replace("Z", ""))
        
        time_span_hours = (last_ts - first_ts).total_seconds() / 3600.0
        # Time span should be around ~80+ hours (spanning all 4 days, NOT cut off at first day!)
        assert time_span_hours >= 70.0, f"Timeline was truncated prematurely! Only spans {time_span_hours} hours."
        
        # Balance should end at the latest balance point (~12497.5)
        assert snaps[-1]["balance"] >= 12000.0

@pytest.mark.asyncio
async def test_bug2_copied_wallets_includes_unrealized_mtm_pnl():
    """
    Bug 2 Verification:
    Ensure get_copied_wallet_stats returns netPnl and mirroredPnl that include
    mark-to-market unrealized gains/losses for open FILLED trades, instead of $0.00.
    """
    whale1 = "0xr4_whale_alpha"
    whale2 = "0xr4_whale_beta"

    async with SessionLocal() as db:
        db.add(Wallet(address=whale1, name="Alpha Whale", status="active", baleen_score=95.0))
        db.add(Wallet(address=whale2, name="Beta Whale", status="active", baleen_score=85.0))

        # Whale 1: Open trade with +$500 unrealized gain
        log1 = ExecutionLog(
            source_wallet_address=whale1,
            market_condition_id="0xcond_r4_1",
            market_question="Market 1",
            side="BUY",
            whale_entry_price=0.50,
            user_fill_price=0.50,
            notional_usd=1000.0,
            fee_usd=5.0,
            status="FILLED", # OPEN!
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        db.add(log1)
        await db.flush()
        
        # Set MTM price to 0.75 (+50% gross = +$500 gross - $5 fee = +$495 net)
        _last_known_pnl[str(log1.id)] = 495.00

        # Whale 2: Closed trade with +$200 realized gain
        log2 = ExecutionLog(
            source_wallet_address=whale2,
            market_condition_id="0xcond_r4_2",
            market_question="Market 2",
            side="BUY",
            whale_entry_price=0.40,
            user_fill_price=0.40,
            notional_usd=500.0,
            fee_usd=2.5,
            realized_pnl_usd=200.00,
            status="CLOSED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        db.add(log2)
        await db.commit()

    async with SessionLocal() as db:
        stats = await get_copied_wallet_stats(db=db)
        
        alpha_stats = next((s for s in stats if s["address"].lower() == whale1.lower()), None)
        beta_stats = next((s for s in stats if s["address"].lower() == whale2.lower()), None)

        assert alpha_stats is not None
        assert beta_stats is not None

        # Alpha Whale had an open trade: mirroredPnl MUST be +$495.00, NOT $0.00!
        assert alpha_stats["mirroredPnl"] == 495.00
        assert alpha_stats["netPnl"] == 495.00

        # Beta Whale had a closed trade: mirroredPnl MUST be +$200.00
        assert beta_stats["mirroredPnl"] == 200.00
        assert beta_stats["netPnl"] == 200.00

@pytest.mark.asyncio
async def test_bug3_poller_blocks_demoted_and_non_top10_buys():
    """
    Bug 3 Verification:
    Verify that in live_poller:
    - Whales outside top 10 cannot open new BUY positions.
    - Demoted whales cannot open new BUY positions.
    - Demoted whales CAN execute SELL signals to close open positions.
    """
    service = LiveTradeMirrorService()
    now_dt = datetime.utcnow()

    # Create 11 active wallets with scores 80 to 90
    async with SessionLocal() as db:
        for i in range(11):
            db.add(Wallet(
                address=f"0xr4_active_{i:02d}",
                status="active",
                baleen_score=float(80 + i), # 0xr4_active_00 is rank 11 (lowest score: 80.0)
                dormant=False,
                is_hft=False,
                avg_trades_per_day=5.0
            ))
        
        # Demoted whale with an open BUY position
        db.add(Wallet(
            address="0xr4_demoted_whale",
            status="rejected",
            baleen_score=20.0,
            dormant=False,
            is_hft=False,
            avg_trades_per_day=5.0
        ))
        open_buy = ExecutionLog(
            source_wallet_address="0xr4_demoted_whale",
            market_condition_id="0xcond_exit_test",
            market_question="Exit Question",
            side="BUY",
            whale_entry_price=0.50,
            user_fill_price=0.50,
            notional_usd=100.0,
            fee_usd=1.0,
            status="FILLED",
            resolution_outcome="Yes",
            executed_at=now_dt - timedelta(hours=2)
        )
        db.add(open_buy)
        await db.commit()

    # 1. 11th whale (0xr4_active_00, score 80.0) tries to BUY -> MUST BE BLOCKED
    await service.process_trade_fill(
        wallet_address="0xr4_active_00",
        condition_id="0xcond_blocked_11",
        title="Blocked Market",
        side="BUY",
        price=0.50,
        cash_usd=100.0,
        dt=now_dt,
        tx_hash="0xtx_rank11_buy",
        log_index=0
    )

    async with SessionLocal() as db:
        log = (await db.execute(select(ExecutionLog).where(ExecutionLog.onchain_tx_hash == "0xtx_rank11_buy"))).scalar_one_or_none()
        assert log is None, "Whale outside Top 10 must NOT open new positions!"

    # 2. Demoted whale tries to BUY -> MUST BE BLOCKED
    await service.process_trade_fill(
        wallet_address="0xr4_demoted_whale",
        condition_id="0xcond_blocked_demoted",
        title="Blocked Market Demoted",
        side="BUY",
        price=0.50,
        cash_usd=100.0,
        dt=now_dt,
        tx_hash="0xtx_demoted_buy",
        log_index=0
    )

    async with SessionLocal() as db:
        log = (await db.execute(select(ExecutionLog).where(ExecutionLog.onchain_tx_hash == "0xtx_demoted_buy"))).scalar_one_or_none()
        assert log is None, "Demoted whale must NOT open new BUY positions!"

    # 3. Top 10 whale (0xr4_active_10, score 90.0) tries to BUY -> MUST SUCCEED
    await service.process_trade_fill(
        wallet_address="0xr4_active_10",
        condition_id="0xcond_allowed_top10",
        title="Allowed Top 10 Market",
        side="BUY",
        price=0.50,
        cash_usd=100.0,
        dt=now_dt,
        tx_hash="0xtx_top10_buy",
        log_index=0
    )

    async with SessionLocal() as db:
        log = (await db.execute(select(ExecutionLog).where(
            ExecutionLog.onchain_tx_hash == "0xtx_top10_buy",
            ExecutionLog.user_id.is_(None)
        ))).scalar_one_or_none()
        assert log is not None, "Top 10 whale BUY must execute successfully!"
        assert log.status == "FILLED"

    # 4. Demoted whale sends SELL for its open position -> MUST EXECUTE TO CLOSE
    await service.process_trade_fill(
        wallet_address="0xr4_demoted_whale",
        condition_id="0xcond_exit_test",
        title="Exit Question",
        side="SELL",
        price=0.60,
        cash_usd=100.0,
        dt=now_dt,
        tx_hash="0xtx_demoted_sell",
        log_index=0
    )

    async with SessionLocal() as db:
        closed_buys = (await db.execute(select(ExecutionLog).where(ExecutionLog.source_wallet_address == "0xr4_demoted_whale", ExecutionLog.side == "BUY", ExecutionLog.status == "CLOSED"))).scalars().all()
        assert len(closed_buys) >= 1, "Demoted whale SELL must close open position!"
        
        sell_log = (await db.execute(select(ExecutionLog).where(
            ExecutionLog.onchain_tx_hash == "0xtx_demoted_sell",
            ExecutionLog.user_id.is_(None)
        ))).scalar_one_or_none()
        assert sell_log is not None, "Demoted whale SELL must create execution log!"
        assert sell_log.status == "CLOSED"

@pytest.mark.asyncio
async def test_bug2_deduplication_of_paired_closed_trades():
    """
    Ensure get_copied_wallet_stats deduplicates paired round-trip trades
    where both BUY (status=CLOSED) and SELL (status=CLOSED) have realized_pnl_usd set,
    preventing 2x trades_copied, 2x total_notional, and 2x net_pnl.
    """
    whale = "0xr4_whale_paired"
    cid = "0xcond_paired_test"

    async with SessionLocal() as db:
        db.add(Wallet(address=whale, name="Paired Whale", status="active", baleen_score=88.0))

        # Closed BUY leg
        buy_leg = ExecutionLog(
            source_wallet_address=whale,
            market_condition_id=cid,
            market_question="Paired Market",
            side="BUY",
            whale_entry_price=0.50,
            user_fill_price=0.50,
            notional_usd=100.0,
            fee_usd=2.5,
            realized_pnl_usd=50.00,
            status="CLOSED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        # Closed SELL leg
        sell_leg = ExecutionLog(
            source_wallet_address=whale,
            market_condition_id=cid,
            market_question="Paired Market",
            side="SELL",
            whale_entry_price=0.75,
            user_fill_price=0.75,
            notional_usd=100.0,
            fee_usd=1.5,
            realized_pnl_usd=50.00,
            status="CLOSED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        db.add(buy_leg)
        db.add(sell_leg)
        await db.commit()

    async with SessionLocal() as db:
        stats = await get_copied_wallet_stats(db=db)
        whale_stats = next((s for s in stats if s["address"].lower() == whale.lower()), None)
        assert whale_stats is not None

        # Should be strictly 1 trade copied (not 2!), $100 notional (not $200!), +$50.00 net PnL (not +$100.00!)
        assert whale_stats["tradesCopied"] == 1
        assert whale_stats["totalNotional"] == 100.0
        assert whale_stats["netPnl"] == 50.00
        assert whale_stats["mirroredPnl"] == 50.00
        assert whale_stats["wins"] == 1
        assert whale_stats["losses"] == 0

@pytest.mark.asyncio
async def test_param_alias_userId_and_user_id():
    """
    Ensure endpoints accept both camelCase 'userId' and snake_case 'user_id' aliases cleanly.
    """
    import uuid
    from app.api.execution_logs import get_portfolio_summary

    test_uid = str(uuid.uuid4())
    unique_email = f"r4user_{uuid.uuid4().hex[:8]}@baleen.ai"
    try:
        async with SessionLocal() as db:
            db.add(User(id=uuid.UUID(test_uid), email=unique_email))
            await db.commit()

        async with SessionLocal() as db:
            # Both parameter styles should return without errors
            stats1 = await get_copied_wallet_stats(user_id=test_uid, db=db)
            stats2 = await get_copied_wallet_stats(userId=test_uid, db=db)
            assert stats1 == stats2

            snaps1 = await get_portfolio_snapshots(user_id=test_uid, timeframe="all", db=db)
            snaps2 = await get_portfolio_snapshots(userId=test_uid, timeframe="all", db=db)
            assert len(snaps1) == len(snaps2)

            summary1 = await get_portfolio_summary(user_id=test_uid, timeframe="all", db=db)
            summary2 = await get_portfolio_summary(userId=test_uid, timeframe="all", db=db)
            assert summary1["currentBalance"] == summary2["currentBalance"]
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id == uuid.UUID(test_uid)))
            await db.commit()

@pytest.mark.asyncio
async def test_portfolio_summary_deduplicates_trade_counts():
    """
    Ensure get_portfolio_summary returns deduplicated filledTradesCount,
    closedTradesCount, and holdingTradesCount when paired round-trip trades exist.
    """
    from app.api.execution_logs import get_portfolio_summary

    cid = "0xcond_summary_dedup"
    whale = "0xr4_whale_sum_dedup"

    async with SessionLocal() as db:
        # 1 closed round trip (BUY + SELL)
        buy_log = ExecutionLog(
            source_wallet_address=whale,
            market_condition_id=cid,
            market_question="Summary Market",
            side="BUY",
            whale_entry_price=0.50,
            user_fill_price=0.50,
            notional_usd=100.0,
            fee_usd=2.5,
            realized_pnl_usd=50.00,
            status="CLOSED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        sell_log = ExecutionLog(
            source_wallet_address=whale,
            market_condition_id=cid,
            market_question="Summary Market",
            side="SELL",
            whale_entry_price=0.75,
            user_fill_price=0.75,
            notional_usd=100.0,
            fee_usd=1.5,
            realized_pnl_usd=50.00,
            status="CLOSED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        # 1 open holding trade (BUY only)
        open_buy = ExecutionLog(
            source_wallet_address=whale,
            market_condition_id="0xcond_summary_open",
            market_question="Summary Market Open",
            side="BUY",
            whale_entry_price=0.40,
            user_fill_price=0.40,
            notional_usd=50.0,
            fee_usd=1.0,
            status="FILLED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        db.add(buy_log)
        db.add(sell_log)
        db.add(open_buy)
        await db.commit()

    async with SessionLocal() as db:
        summary = await get_portfolio_summary(db=db)
        # Total distinct trades: 1 closed + 1 open = 2 trades (NOT 3!)
        assert summary["filledTradesCount"] == 2
        assert summary["holdingTradesCount"] == 1
        assert summary["closedTradesCount"] == 1
        assert summary["allTimeWins"] == 1
        assert summary["allTimeLosses"] == 0
        assert summary["totalNotionalInvested"] == 150.0 # 100 + 50 (NOT 250!)

@pytest.mark.asyncio
async def test_mark_to_market_deduplicates_closed_trades_pnl():
    """
    Ensure MarkToMarketService correctly counts closed platform and user realized PnL
    without doubling due to paired BUY and SELL rows.
    """
    from app.services.mark_to_market import MarkToMarketService, _closed_trades_cache
    _closed_trades_cache["ts"] = 0.0 # force refresh

    whale = "0xr4_whale_mtm_dedup"
    cid = "0xcond_mtm_dedup"

    async with SessionLocal() as db:
        buy_log = ExecutionLog(
            source_wallet_address=whale,
            market_condition_id=cid,
            market_question="MTM Market",
            side="BUY",
            whale_entry_price=0.50,
            user_fill_price=0.50,
            notional_usd=200.0,
            fee_usd=3.0,
            realized_pnl_usd=75.00,
            status="CLOSED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        sell_log = ExecutionLog(
            source_wallet_address=whale,
            market_condition_id=cid,
            market_question="MTM Market",
            side="SELL",
            whale_entry_price=0.75,
            user_fill_price=0.75,
            notional_usd=200.0,
            fee_usd=2.0,
            realized_pnl_usd=75.00,
            status="CLOSED",
            resolution_outcome="Yes",
            executed_at=datetime.utcnow()
        )
        db.add(buy_log)
        db.add(sell_log)
        await db.commit()

    mtm_svc = MarkToMarketService()
    await mtm_svc.update_valuations_and_consensus()

    # platform_realized_pnl MUST be 75.00, NOT 150.00!
    assert _closed_trades_cache["platform_realized_pnl"] == 75.00
    # platform_closed_count MUST be 1, NOT 2!
    assert _closed_trades_cache["platform_closed_count"] == 1

