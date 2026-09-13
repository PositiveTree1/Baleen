import uuid
from datetime import datetime, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from fastapi import HTTPException
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import User, ExecutionLog, PortfolioSnapshot, SandboxRun, Wallet
from app.services.paper_runs import archive_and_start
from app.services.paper_accounting import paper_totals
from app.api.users import paper_run_trades
from app.api.execution_logs import get_portfolio_snapshots

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL port 55432')


@pytest.mark.asyncio
async def test_reset_preserves_evidence_isolates_cash_and_authorizes_archive_reads(pg):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    async with sessions() as db:
        owner = User(email=f'{uuid.uuid4()}@paper.test', sandbox_balance_usd=9900)
        other = User(email=f'{uuid.uuid4()}@paper.test')
        db.add_all([owner, other])
        await db.flush()
        old = ExecutionLog(user_id=owner.id, is_sandbox=True, side='BUY', status='FILLED',
                           notional_usd=100, user_fill_price=.5, fee_usd=0)
        live = ExecutionLog(user_id=owner.id, is_sandbox=False, side='BUY', status='FILLED')
        separate = ExecutionLog(user_id=other.id, is_sandbox=True, side='BUY', status='FILLED')
        db.add_all([old, live, separate])
        await db.commit()
        successor = await archive_and_start(db, owner, 15000)
        await db.commit()
        archived = (await db.execute(select(SandboxRun).where(SandboxRun.user_id == owner.id,
                                    SandboxRun.status == 'ARCHIVED'))).scalar_one()
        visible = (await db.execute(select(ExecutionLog))).scalars().all()
        assert {r.id for r in visible} == {live.id, separate.id}
        audit = (await db.execute(select(ExecutionLog).execution_options(include_archived_runs=True))).scalars().all()
        assert len(audit) == 3
        assert (await paper_totals(db, owner.id, 15000))['cash'] == 15000
        assert successor.source_cutoff_at is not None
        history = await paper_run_trades(str(owner.id), str(archived.id), owner, db)
        assert len(history) == 1 and history[0]['notionalUsd'] == 100
        with pytest.raises(HTTPException) as exc:
            await paper_run_trades(str(owner.id), str(archived.id), other, db)
        assert exc.value.status_code == 403
        snapshots = (await db.execute(select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == owner.id))).scalars().all()
        assert len(snapshots) == 1 and snapshots[0].run_id == successor.id
        assert snapshots[0].balance == 15000
        from app.api.admin import export_trades_csv
        import csv
        import io
        exported = await export_trades_csv(owner, db)
        records = list(csv.DictReader(io.StringIO(exported.body.decode())))
        historic = next(r for r in records if r['Execution ID'] == str(old.id))
        assert historic['Run ID'] == str(archived.id) and historic['User ID'] == str(owner.id)
        assert historic['Recorded Realized PnL USD'] == ''
        assert float(historic['Recorded Fee USD']) == 0


@pytest.mark.asyncio
async def test_snapshot_api_returns_only_recorded_values_and_timestamps(pg):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    stamp = datetime.utcnow() - timedelta(minutes=10, seconds=23)
    async with sessions() as db:
        db.add(PortfolioSnapshot(timestamp=stamp, balance=0, total_pnl=-5000, active_trades_count=0))
        await db.commit()
        rows = await get_portfolio_snapshots(user_id=None, userId=None, timeframe='all', limit=100,
                                             current_user=None, db=db)
        assert len(rows) == 1
        assert rows[0]['balance'] == 0 and rows[0]['timestamp'] == stamp.isoformat() + 'Z'
        assert rows[0]['pnl'] == -5000


@pytest.mark.asyncio
async def test_summary_and_wallet_stats_never_turn_unknown_marks_into_zero(pg):
    from app.api.execution_logs import get_portfolio_summary
    from app.api.wallets import get_copied_wallet_stats
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    async with sessions() as db:
        user = User(email=f'{uuid.uuid4()}@truth.test', sandbox_balance_usd=10000,
                    sandbox_starting_balance_usd=10000)
        db.add(user)
        db.add(Wallet(address='0x'+'a'*40))
        await db.flush()
        db.add_all([
            ExecutionLog(user_id=user.id, source_wallet_address='0x'+'a'*40, is_sandbox=True,
                side='BUY', status='CLOSED', realized_pnl_usd=12, fee_usd=0, notional_usd=100),
            ExecutionLog(user_id=user.id, source_wallet_address='0x'+'a'*40, is_sandbox=True,
                side='BUY', status='FILLED', token_id='unknown-fixture', user_fill_price=.5,
                fee_usd=0, notional_usd=100),
            ExecutionLog(user_id=user.id, source_wallet_address='0x'+'a'*40, is_sandbox=False,
                side='BUY', status='CLOSED', realized_pnl_usd=99999, fee_usd=0, notional_usd=100)])
        await db.commit()
        summary = await get_portfolio_summary(str(user.id), None, None, user, db)
        assert summary['currentBalance'] is None and summary['totalPnlUsd'] is None
        assert summary['unvaluedTradesCount'] == 1 and summary['knownPnlUsd'] == 12
        assert summary['totalFeesPaidUsd'] == 0 and summary['allTimeWinRate'] == 100
        assert summary['filledTradesCount'] == 2
        stats = await get_copied_wallet_stats(str(user.id), None, user, db)
        assert stats[0]['netPnl'] is None and stats[0]['knownPnlUsd'] == 12
        assert stats[0]['unvaluedTradesCount'] == 1 and stats[0]['wins'] == 1


@pytest.mark.asyncio
async def test_concurrent_resets_leave_one_active_run_and_preserve_both_genesis_records(pg):
    import asyncio
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    async with sessions() as db:
        user = User(email=f'{uuid.uuid4()}@concurrent.test')
        db.add(user)
        await db.commit()
        uid = user.id
    async def reset(balance):
        async with sessions() as db:
            user = await db.get(User, uid)
            run = await archive_and_start(db, user, balance)
            await db.commit()
            return run.id
    ids = await asyncio.gather(reset(10000), reset(15000))
    async with sessions() as db:
        user = await db.get(User, uid)
        runs = (await db.execute(select(SandboxRun).where(SandboxRun.user_id == uid))).scalars().all()
        assert len(runs) == 3 and sum(r.status == 'ACTIVE' for r in runs) == 1
        assert user.active_paper_run_id in ids
        snapshots = (await db.execute(select(PortfolioSnapshot).execution_options(include_archived_runs=True)
            .where(PortfolioSnapshot.user_id == uid))).scalars().all()
        assert {s.run_id for s in snapshots} == set(ids)
