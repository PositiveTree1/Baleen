"""Real PostgreSQL review checks; uses the guarded disposable schema fixture."""
import asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import User, Wallet, SignalInbox, ExecutionLog
from app.api.signals import WhaleTradeSignalPayload, receive_whale_signal
from app.services import signal_worker, live_poller

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated PostgreSQL port 55432')


@pytest.mark.asyncio
async def test_old_counterparty_queue_entry_is_quarantined_without_copying(pg, monkeypatch):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    monkeypatch.setattr(signal_worker, 'SessionLocal', sessions)
    service = AsyncMock()
    monkeypatch.setattr(live_poller, 'live_trade_mirror', service)
    p = payload().model_copy(update={'isMaker':False})
    async with sessions() as db:
        result = await receive_whale_signal(p, BackgroundTasks(), db, True)
    await signal_worker.drain_signal_inbox()
    service.process_onchain_signal.assert_not_awaited()
    async with sessions() as db:
        row = await db.get(SignalInbox, uuid.UUID(result['inboxId']))
        assert row.status == 'QUARANTINED' and 'Counterparty' in row.error_detail


@pytest.mark.asyncio
async def test_listener_includes_live_policy_and_held_sources(pg):
    from app.api.signals import watched_wallets
    from app.models import LiveCopyPolicy, LiveExecutionAccount, LiveSourcePosition
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    uid = uuid.uuid4()
    selected, held = '0x'+'a'*40, '0x'+'b'*40
    async with sessions() as db, db.begin():
        db.add(User(id=uid, email='watched-live@example.test'))
        await db.flush()
        db.add(LiveExecutionAccount(user_id=uid, run_id=uuid.uuid4(), wallet_address='0x'+'c'*40, enabled=True))
        db.add(LiveCopyPolicy(user_id=uid, revision=1, source_wallets=[selected], copy_ratio='.1', limits={}))
        await db.flush()
        db.add(LiveSourcePosition(user_id=uid, source_wallet_address=held, token_id='111', quantity=5))
    async with sessions() as db:
        assert await watched_wallets(db, True) == sorted([selected, held])
        (await db.get(LiveExecutionAccount, uid)).enabled = False
        await db.commit()
        assert await watched_wallets(db, True) == [held]


def payload():
    return WhaleTradeSignalPayload(walletAddress='0x' + 'a' * 40, side='BUY',
        assetId='111', amountFilled='100000000', amountUnit='raw_6', price='0.5',
        transactionHash='0x' + uuid.uuid4().hex * 2, logIndex=4,
        blockNumber=100, timestamp=1788880000000)


@pytest.mark.asyncio
async def test_concurrent_inbox_acceptance_survives_connection_restart(pg, monkeypatch):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    p = payload()
    async def accept():
        async with sessions() as db:
            return await receive_whale_signal(p, BackgroundTasks(), db, True)
    results = await asyncio.gather(*(accept() for _ in range(8)))
    assert len({r['inboxId'] for r in results}) == 1
    await pg.dispose()
    async with sessions() as db:
        assert (await db.execute(select(func.count()).select_from(SignalInbox))).scalar_one() == 1
        changed = p.model_copy(update={'amountFilled': '200000000'})
        with pytest.raises(HTTPException) as exc:
            await receive_whale_signal(changed, BackgroundTasks(), db, True)
        assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_persisted_inbox_recovery_runs_real_consumer_once(pg, monkeypatch):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    monkeypatch.setattr(signal_worker, 'SessionLocal', sessions)
    monkeypatch.setattr(live_poller, 'SessionLocal', sessions)
    service = live_poller.LiveTradeMirrorService()
    monkeypatch.setattr(live_poller, 'live_trade_mirror', service)
    service._resolve_market_metadata = AsyncMock(return_value={
        'condition_id': '0x' + 'b' * 64, 'title': 'Recorded market', 'event_slug': 'recorded', 'icon': 'recorded'})
    p = payload()
    async with sessions() as db:
        db.add(Wallet(address=p.walletAddress, status='active', tier='gold_sniper',
                      dormant=False, is_hft=False, avg_trades_per_day=2, baleen_score=100,
                      all_time_pnl_usd=50000, win_rate_pct=90, wilson_lb=85))
        user = User(email='recovery@example.test', sandbox_starting_balance_usd=10000,
                    sandbox_balance_usd=10000, sandbox_high_water_mark_usd=10000)
        db.add(user)
        await db.commit()
        uid = user.id
        result = await receive_whale_signal(p, BackgroundTasks(), db, True)
    # No HTTP background callback ran. A new worker must recover committed work.
    await pg.dispose()
    with patch('app.services.event_logger.log_event', new=AsyncMock()):
        await signal_worker.drain_signal_inbox()
        async with sessions() as db:
            row = await db.get(SignalInbox, uuid.UUID(result['inboxId']))
            assert row.status == 'PROCESSED', row.error_detail
            # Simulate death after effects committed but before inbox completion.
            row.status = 'PENDING'
            await db.commit()
        await signal_worker.drain_signal_inbox()
    async with sessions() as db:
        count = (await db.execute(select(func.count()).select_from(ExecutionLog).where(
            ExecutionLog.user_id == uid, ExecutionLog.onchain_tx_hash == p.transactionHash))).scalar_one()
        assert count == 1
