import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import User, LiveExecutionAccount, LiveOrderIntent, LivePosition
from app.services.live_order_journal import LiveOrderJournal
from app.services.clob_gateway import SubmissionUncertain

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL port 55432')


@pytest.mark.asyncio
async def test_source_exit_cannot_spend_other_trader_allocation(pg):
    from app.models import LiveSourcePosition
    sessions, journal, uid, run = await fixture(pg)
    source_a, source_b = '0x'+'a'*40, '0x'+'b'*40
    async with sessions() as db, db.begin():
        db.add(LivePosition(user_id=uid, token_id='111', quantity=100, reserved_quantity=0, cost_basis=40))
        db.add_all([LiveSourcePosition(user_id=uid, source_wallet_address=source_a, token_id='111', quantity=20),
            LiveSourcePosition(user_id=uid, source_wallet_address=source_b, token_id='111', quantity=80)])
    request = {**intent(uid, run, 'exit-a', qty='21', side='SELL'), 'risk_context':{'source_wallet':source_a}}
    with pytest.raises(ValueError):
        await journal.prepare(**request)
    request = {**intent(uid, run, 'exit-a', qty='20', side='SELL'), 'risk_context':{'source_wallet':source_a}}
    oid = await journal.prepare(**request)
    with pytest.raises(ValueError):
        await journal.prepare(**{**intent(uid, run, 'exit-a-duplicate', qty='1', side='SELL'),
                                 'risk_context':{'source_wallet':source_a}})
    gateway = AsyncMock()
    gateway.submit_signed_order.return_value = {'success':True, 'orderID':request['signed_order_hash']}
    await journal.submit(user_id=uid, order_id=oid, gateway=gateway)
    await journal.record_confirmed_fill(user_id=uid, order_id=oid, trade_id='source-a-exit', quantity=20, price='.5', fee=0)
    async with sessions() as db:
        assert (await db.get(LiveSourcePosition, (uid, source_a, '111'))).quantity == 0
        assert (await db.get(LiveSourcePosition, (uid, source_b, '111'))).quantity == 80
        assert (await db.get(LivePosition, (uid, '111'))).quantity == 80


async def fixture(pg):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    uid, run = uuid.uuid4(), uuid.uuid4()
    async with sessions() as db, db.begin():
        db.add(User(id=uid, email=f'{uid}@journal.test'))
        await db.flush()
        db.add(LiveExecutionAccount(user_id=uid, run_id=run, wallet_address='0x' + '1' * 40,
            cash=100, reserved_cash=0, enabled=True, reconciled_at=datetime.utcnow()))
    # These tests isolate journaling from the separately tested signing/risk gate.
    return sessions, LiveOrderJournal(sessions, submission_gate=AsyncMock(return_value=True)), uid, run


def intent(uid, run, key='first', qty='100', side='BUY', fee='0'):
    amount = Decimal(qty)
    raw_qty, raw_cash = str(int(amount * 1000000)), str(int(amount * Decimal('.5') * 1000000))
    return dict(user_id=uid, run_id=run, intent_key=key, token_id='111', side=side,
        quantity=qty, limit_price='.5', fee_budget=fee,
        signed_order_hash='0x' + uuid.uuid4().hex * 2,
        envelope={'order': {'maker': '0x' + '1' * 40, 'side': side, 'tokenId': '111',
            'makerAmount': raw_cash if side == 'BUY' else raw_qty,
            'takerAmount': raw_qty if side == 'BUY' else raw_cash, 'signature': 'fixture-signature'}})


@pytest.mark.asyncio
async def test_concurrent_reservations_cannot_spend_same_cash(pg):
    sessions, journal, uid, run = await fixture(pg)
    results = await asyncio.gather(journal.prepare(**intent(uid, run, 'a', qty='140')),
                                   journal.prepare(**intent(uid, run, 'b', qty='140')), return_exceptions=True)
    assert sum(isinstance(r, uuid.UUID) for r in results) == 1
    assert sum(isinstance(r, ValueError) for r in results) == 1
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert account.cash == 100 and account.reserved_cash == 70


@pytest.mark.asyncio
async def test_timeout_recovery_does_not_resubmit_or_release_cash(pg):
    sessions, journal, uid, run = await fixture(pg)
    order_id = await journal.prepare(**intent(uid, run))
    gateway = AsyncMock()
    gateway.submit_signed_order.side_effect = SubmissionUncertain('fixture timeout')
    with pytest.raises(SubmissionUncertain):
        await journal.submit(user_id=uid, order_id=order_id, gateway=gateway)
    await pg.dispose()
    with pytest.raises(ValueError):
        await LiveOrderJournal(sessions).submit(user_id=uid, order_id=order_id, gateway=gateway)
    with pytest.raises(ValueError):
        await journal.finalize_cancel(user_id=uid, order_id=order_id,
            reconciled_filled_quantity=0, exchange_status='UNKNOWN')
    assert gateway.submit_signed_order.await_count == 1
    async with sessions() as db:
        assert (await db.get(LiveOrderIntent, order_id)).state == 'UNKNOWN'
        assert (await db.get(LiveExecutionAccount, uid)).reserved_cash == 50


@pytest.mark.asyncio
async def test_confirmed_partial_fills_and_cancellation_conserve_money(pg):
    sessions, journal, uid, run = await fixture(pg)
    request = intent(uid, run)
    order_id = await journal.prepare(**request)
    assert await journal.prepare(**request) == order_id
    gateway = AsyncMock()
    gateway.submit_signed_order.return_value = {'success': True, 'orderID': request['signed_order_hash']}
    await journal.submit(user_id=uid, order_id=order_id, gateway=gateway)
    fill = dict(user_id=uid, order_id=order_id, trade_id='confirmed-one', quantity='20', price='.5', fee='0')
    assert await journal.record_confirmed_fill(**fill)
    assert not await journal.record_confirmed_fill(**fill)
    with pytest.raises(ValueError):
        await journal.record_confirmed_fill(**{**fill, 'quantity': '21'})
    await journal.finalize_cancel(user_id=uid, order_id=order_id,
                                  reconciled_filled_quantity='20', exchange_status='CANCELED')
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        position = await db.get(LivePosition, (uid, '111'))
        assert account.cash == 90 and account.reserved_cash == 0
        assert position.quantity == 20 and position.cost_basis == 10
        assert (await db.get(LiveOrderIntent, order_id)).state == 'CANCELLED'


@pytest.mark.asyncio
async def test_sell_reserves_shares_and_cannot_short_or_cross_account(pg):
    sessions, journal, uid, run = await fixture(pg)
    async with sessions() as db, db.begin():
        db.add(LivePosition(user_id=uid, token_id='111', quantity=20, reserved_quantity=0, cost_basis=8))
    with pytest.raises(ValueError):
        await journal.prepare(**intent(uid, run, qty='21', side='SELL'))
    request = intent(uid, run, qty='20', side='SELL')
    order_id = await journal.prepare(**request)
    with pytest.raises(ValueError):
        await journal.submit(user_id=uuid.uuid4(), order_id=order_id, gateway=AsyncMock())
    gateway = AsyncMock()
    gateway.submit_signed_order.return_value = {'success': True, 'orderID': request['signed_order_hash']}
    await journal.submit(user_id=uid, order_id=order_id, gateway=gateway)
    await journal.record_confirmed_fill(user_id=uid, order_id=order_id, trade_id='sell', quantity='20', price='.5', fee='1')
    async with sessions() as db:
        position = await db.get(LivePosition, (uid, '111'))
        assert position.quantity == 0 and position.reserved_quantity == 0 and position.cost_basis == 0
        assert (await db.get(LiveExecutionAccount, uid)).cash == 109
        assert not (await db.get(LiveExecutionAccount, uid)).enabled  # Fee exceeded the zero budget.


@pytest.mark.asyncio
async def test_stale_reconciliation_blocks_submission_without_releasing_reservation(pg):
    sessions, journal, uid, run = await fixture(pg)
    order_id = await journal.prepare(**intent(uid, run))
    async with sessions() as db, db.begin():
        account = await db.get(LiveExecutionAccount, uid)
        account.reconciled_at = datetime.utcnow() - timedelta(seconds=31)
    gateway = AsyncMock()
    with pytest.raises(PermissionError):
        await journal.submit(user_id=uid, order_id=order_id, gateway=gateway)
    gateway.submit_signed_order.assert_not_awaited()
    async with sessions() as db:
        assert (await db.get(LiveOrderIntent, order_id)).state == 'PREPARED'
        assert (await db.get(LiveExecutionAccount, uid)).reserved_cash == 50


@pytest.mark.asyncio
@pytest.mark.parametrize('approval', [None, False])
async def test_missing_or_rejected_submission_gate_never_sends_order(pg, approval):
    sessions, journal, uid, run = await fixture(pg)
    order_id = await journal.prepare(**intent(uid, run))
    gate = None if approval is None else AsyncMock(return_value=False)
    gateway = AsyncMock()
    with pytest.raises(PermissionError):
        await LiveOrderJournal(sessions, submission_gate=gate).submit(user_id=uid, order_id=order_id, gateway=gateway)
    gateway.submit_signed_order.assert_not_awaited()
    async with sessions() as db:
        assert (await db.get(LiveOrderIntent, order_id)).state == 'PREPARED'
        assert (await db.get(LiveExecutionAccount, uid)).reserved_cash == 50
