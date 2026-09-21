import asyncio
import uuid
import pytest
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.test_real_postgres_batch_a import pg, initialize, URL
from tests.test_paper_copy_research import ADDRESS, leg, append
from app.models import User, PaperCopyResearchRun, PaperCopyResearchEvent
from app.services.paper_copy_research import start_run
from app.migrations import run_versioned_migrations

pytestmark = pytest.mark.skipif(not URL, reason="Requires isolated local PostgreSQL")


@pytest.mark.asyncio
async def test_concurrent_retry_books_one_trade_and_migration_restores_tables(pg):
    await initialize(pg)
    # Exercise migration DDL directly, without create_all masking missing tables.
    async with pg.begin() as conn:
        await conn.execute(text("DROP TABLE paper_copy_sniper_allocations"))
        await conn.execute(text("DROP TABLE paper_copy_research_events"))
        await conn.execute(text("DROP TABLE paper_copy_research_runs"))
        await conn.execute(text("DELETE FROM schema_migrations WHERE version IN (23, 25)"))
        await run_versioned_migrations(conn)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    owner = uuid.uuid4()
    async with sessions() as db, db.begin():
        db.add(User(id=owner, email=f"{owner}@example.test"))
        await db.flush()
        run = await start_run(db, user_id=owner, source_wallet=ADDRESS, starting_cash=100,
                              ratio=".1", source_cutoff=10)
        run_id = run.id
    outcomes = await asyncio.gather(*(append(sessions, owner, run_id, leg("same-receipt", 10)) for _ in range(4)))
    assert all(report == outcomes[0] for report in outcomes)
    async with sessions() as db:
        run = await db.get(PaperCopyResearchRun, run_id)
        assert run.revision == 1
        assert run.policy["ratio"] == "0.1"
        assert run.report["valuation"]["cash"] == "94.99"
        assert (await db.execute(select(func.count()).select_from(PaperCopyResearchEvent))).scalar() == 1


@pytest.mark.asyncio
async def test_live_worker_concurrency_and_reset_do_not_double_book(pg, monkeypatch):
    from datetime import datetime, timedelta
    from decimal import Decimal
    from unittest.mock import AsyncMock
    from tests.test_paper_copy_pipeline import book, market, CONDITION
    from app.models import Wallet, CanonicalSourceEvent
    from app.api.paper_copy import start_paper_copy, StartPaperCopy
    from app.services.paper_copy_worker import process_run
    from app.services.paper_runs import archive_and_start
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    uid = uuid.uuid4()
    async with sessions() as db, db.begin():
        db.add(User(id=uid, email='pipeline-pg@example.test', sandbox_starting_balance_usd=100,
                    sandbox_balance_usd=100, sandbox_high_water_mark_usd=100))
        db.add(Wallet(address=ADDRESS, status='tracked'))
    monkeypatch.setattr('app.api.paper_copy.accounting_snapshot', AsyncMock(return_value={
        'status':'observed', 'requested_wallet':ADDRESS, 'equity_usd':'1000',
        'valuation_time':datetime.utcnow().isoformat()+'Z'}))
    async with sessions() as db:
        user = await db.get(User, uid)
        state = await start_paper_copy(StartPaperCopy(wallets=[ADDRESS], starting_cash=100), user, db)
        rid = state['runs'][0]['id']
        row = await db.get(PaperCopyResearchRun, rid)
        row.policy = {**row.policy, 'source_cutoff':str(datetime.utcnow().timestamp()-10)}
        db.add(CanonicalSourceEvent(source_wallet_address=ADDRESS, condition_id=CONDITION, token_id='123',
            side='BUY', shares=100, price=.5, notional_usd=50, block_time=datetime.utcnow()-timedelta(seconds=1),
            block_number=100, log_index=0, tx_hash='0xpg', block_hash='0xblock', emitting_contract='0xexchange', status='CONFIRMED'))
        await db.commit()
    client, receipts = AsyncMock(), AsyncMock()
    client.fetch_order_book.side_effect = lambda token: book()
    client.fetch_market_info.return_value = market()
    receipts.source.return_value = {'quantity':Decimal(100), 'price':Decimal('.5'), 'cash_amount':Decimal(50)}
    await asyncio.gather(*(process_run(sessions, rid, client, receipts) for _ in range(2)))
    async with sessions() as db:
        run = await db.get(PaperCopyResearchRun, rid)
        assert run.revision == 1 and Decimal(run.report['cash']) == Decimal('94.9')
        await archive_and_start(db, await db.get(User, uid), 200)
        await db.commit()
    await process_run(sessions, rid, client, receipts)
    async with sessions() as db:
        assert (await db.get(PaperCopyResearchRun, rid)).revision == 1
