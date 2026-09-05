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
        await db.commit()
    yield
    async with SessionLocal() as db:
        await db.execute(delete(PortfolioSnapshot))
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xr4_%")))
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
        log = (await db.execute(select(ExecutionLog).where(ExecutionLog.onchain_tx_hash == "0xtx_top10_buy"))).scalar_one_or_none()
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
        
        sell_log = (await db.execute(select(ExecutionLog).where(ExecutionLog.onchain_tx_hash == "0xtx_demoted_sell"))).scalar_one_or_none()
        assert sell_log is not None, "Demoted whale SELL must create execution log!"
        assert sell_log.status == "CLOSED"
