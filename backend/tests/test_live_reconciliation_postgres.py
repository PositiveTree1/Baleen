"""Real DB recovery checks; exchange responses below are explicit synthetic fixtures."""
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from tests.test_real_postgres_batch_a import pg, URL
from tests.test_live_order_journal_postgres import fixture, intent
from app.models import LiveOrderIntent, LiveExecutionAccount, LivePosition, LiveReconciliation
from app.services.live_reconciliation import LiveReconciler

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL')


@pytest.mark.asyncio
@pytest.mark.parametrize('stopped', [False, True])
async def test_waiting_for_confirmation_resumes_reads_without_undoing_an_explicit_stop(pg, stopped):
    sessions, uid, oid, gateway = await setup(pg)
    gateway.trades_for_id.return_value['status'] = 'MINED'
    reconciler = LiveReconciler(sessions)
    assert (await reconciler.reconcile(uid, gateway, 3))['status'] == 'WAITING'
    async with sessions() as db, db.begin():
        account = await db.get(LiveExecutionAccount, uid)
        assert account.enabled and account.reconciled_at is None and account.reserved_cash == 50
        if stopped: account.enabled = False
    gateway.trades_for_id.return_value['status'] = 'CONFIRMED'
    assert (await reconciler.reconcile(uid, gateway, 3))['status'] == 'MATCHED'
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert account.enabled == (not stopped) and account.reconciled_at is not None


@pytest.mark.asyncio
@pytest.mark.parametrize('foreign_position', [False, True])
async def test_bootstrapped_account_checks_all_wallet_holdings_not_only_journal_tokens(pg, monkeypatch, foreign_position):
    from datetime import datetime
    from app.models import LiveWalletBaseline
    from app.services import live_wallet_snapshot
    sessions, uid, oid, gateway = await setup(pg)
    gateway.trades_for_id.return_value['transaction_hash'] = '0x'+'a'*64
    settlements = AsyncMock()
    settlements.fill.return_value = dict(trade_id='polygon:fixture', quantity=20, price='.5', fee=0, cash_amount=10)
    reader = AsyncMock()
    balances = {live_wallet_snapshot.CTF+':111':'20'}
    if foreign_position: balances[live_wallet_snapshot.CTF+':222'] = '1'
    reader.read.return_value = {'cash':90, 'balances':balances}
    monkeypatch.setattr(live_wallet_snapshot, 'LiveWalletSnapshot', lambda _:reader)
    async with sessions() as db, db.begin():
        account = await db.get(LiveExecutionAccount, uid)
        db.add(LiveWalletBaseline(user_id=uid, run_id=account.run_id, starting_cash=100, block_number=1,
            block_hash='0x'+'b'*64, block_time=datetime.utcnow(), observed_tokens=[]))
    result = await LiveReconciler(sessions, settlements).reconcile(uid, gateway, 3)
    assert result['status'] == ('BLOCKED' if foreign_position else 'MATCHED')
    reader.read.assert_awaited_once()
    async with sessions() as db:
        assert (await db.get(LiveExecutionAccount, uid)).cash == 90
        assert await db.get(LivePosition, (uid, '222')) is None


async def setup(pg):
    sessions, journal, uid, run = await fixture(pg)
    request = intent(uid, run)
    oid = await journal.prepare(**request)
    async with sessions() as db, db.begin():
        (await db.get(LiveOrderIntent, oid)).state = 'UNKNOWN'
    gateway = AsyncMock()
    gateway.open_orders.return_value = []
    gateway.get_order.return_value = {
        'id': request['signed_order_hash'], 'maker_address': '0x' + '1' * 40,
        'asset_id': '111', 'side': 'BUY', 'original_size': '100', 'size_matched': '20',
        'price': '.5', 'status': 'CANCELED', 'associate_trades': ['trade-one']}
    gateway.trades_for_id.return_value = {
        'id': 'trade-one', 'status': 'CONFIRMED', 'taker_order_id': request['signed_order_hash'],
        'maker_address': '0x' + '1' * 40, 'asset_id': '111', 'side': 'BUY',
        'size': '20', 'price': '.5', 'fee_rate_bps': '0'}
    gateway.collateral_balance.return_value = {'balance': '90'}
    gateway.token_balance.return_value = 20
    return sessions, uid, oid, gateway


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['CANCELED', 'ORDER_STATUS_CANCELED'])
async def test_unknown_partial_order_recovers_once_across_restart(pg, status):
    sessions, uid, oid, gateway = await setup(pg)
    gateway.get_order.return_value['status'] = status
    assert (await LiveReconciler(sessions).reconcile(uid, gateway, 0))['status'] == 'MATCHED'
    await pg.dispose()
    assert (await LiveReconciler(sessions).reconcile(uid, gateway, 0))['status'] == 'MATCHED'
    gateway.submit_signed_order.assert_not_awaited()
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert account.cash == 90 and account.reserved_cash == 0
        assert (await db.get(LivePosition, (uid, '111'))).quantity == 20
        assert (await db.get(LiveOrderIntent, oid)).state == 'CANCELLED'


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['unconfirmed', 'wrong_wallet', 'missing_fee', 'nonzero_fee', 'incomplete_fills', 'unknown_order'])
async def test_missing_or_conflicting_evidence_preserves_reservations(pg, fault):
    sessions, uid, oid, gateway = await setup(pg)
    trade, remote = gateway.trades_for_id.return_value, gateway.get_order.return_value
    if fault == 'unconfirmed': trade['status'] = 'MATCHED'
    if fault == 'wrong_wallet': trade['maker_address'] = '0x' + '2' * 40
    if fault == 'missing_fee': del trade['fee_rate_bps']
    if fault == 'nonzero_fee': trade['fee_rate_bps'] = '500'
    if fault == 'incomplete_fills': remote['size_matched'] = '21'
    if fault == 'unknown_order': gateway.open_orders.return_value = [{'id': 'other'}]
    expected = 'WAITING' if fault == 'unconfirmed' else 'BLOCKED'
    assert (await LiveReconciler(sessions).reconcile(uid, gateway, 0))['status'] == expected
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert account.enabled == (fault == 'unconfirmed') and account.reconciled_at is None
        assert account.cash == 100 and account.reserved_cash == 50
        assert (await db.execute(select(LiveReconciliation))).scalar_one().status == expected


@pytest.mark.asyncio
async def test_real_balance_discrepancy_halts_without_fabricating_adjustment(pg):
    sessions, uid, oid, gateway = await setup(pg)
    gateway.collateral_balance.return_value = {'balance': '89'}
    result = await LiveReconciler(sessions).reconcile(uid, gateway, 0)
    assert result['status'] == 'BLOCKED'
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert not account.enabled and account.cash == 90  # Proven fill remains booked.


@pytest.mark.asyncio
async def test_stop_request_survives_restart_and_reconciles_fill_before_release(pg):
    from app.api.live_trading import _disable_order_account
    sessions, uid, oid, gateway = await setup(pg)
    async with sessions() as db, db.begin():
        await _disable_order_account(db, uid)
    await pg.dispose()
    assert (await LiveReconciler(sessions).reconcile(uid, gateway, 0))['status'] == 'MATCHED'
    gateway.cancel_order.assert_awaited_once()
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        order = await db.get(LiveOrderIntent, oid)
        assert not account.enabled and account.cash == 90 and account.reserved_cash == 0
        assert order.cancel_requested_at is not None and order.state == 'CANCELLED'
        assert order.filled_quantity == 20


@pytest.mark.asyncio
async def test_cancel_acknowledgement_alone_never_releases_reservations(pg):
    from app.api.live_trading import _disable_order_account
    sessions, uid, oid, gateway = await setup(pg)
    gateway.get_order.side_effect = TimeoutError('fixture unavailable')
    gateway.cancel_order.return_value = {'canceled': ['fixture'], 'not_canceled': {}}
    async with sessions() as db, db.begin():
        await _disable_order_account(db, uid)
    assert (await LiveReconciler(sessions).reconcile(uid, gateway, 0))['status'] == 'BLOCKED'
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert not account.enabled and account.reserved_cash == 50 and account.cash == 100


@pytest.mark.asyncio
async def test_stopped_unsubmitted_order_is_voided_without_exchange_mutation(pg):
    from app.api.live_trading import _disable_order_account
    sessions, journal, uid, run = await fixture(pg)
    oid = await journal.prepare(**intent(uid, run))
    async with sessions() as db, db.begin():
        await _disable_order_account(db, uid)
    gateway = AsyncMock()
    gateway.open_orders.return_value = []
    gateway.collateral_balance.return_value = {'balance': '100'}
    assert (await LiveReconciler(sessions).reconcile(uid, gateway, 0))['status'] == 'MATCHED'
    gateway.cancel_order.assert_not_awaited()
    gateway.submit_signed_order.assert_not_awaited()
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert not account.enabled and account.reserved_cash == 0
        assert (await db.get(LiveOrderIntent, oid)).state == 'VOID'


@pytest.mark.asyncio
async def test_fee_bearing_receipt_groups_api_matches_and_books_once(pg):
    from decimal import Decimal
    from app.models import LiveConfirmedFill
    sessions, uid, oid, gateway = await setup(pg)
    gateway.get_order.return_value['associate_trades'] = ['trade-one', 'trade-two']
    trade = dict(gateway.trades_for_id.return_value, size='10', fee_rate_bps='500', transaction_hash='0x'+'a'*64)
    gateway.trades_for_id.side_effect = [dict(trade, id='trade-one'), dict(trade, id='trade-two')] * 2
    gateway.collateral_balance.return_value = {'balance': '89.75'}
    receipts = AsyncMock()
    receipts.fill.return_value = dict(trade_id='polygon:fixture-order-tx', quantity=Decimal(20),
                                     price=Decimal('.5'), cash_amount=Decimal(10), fee=Decimal('.25'))
    for _ in range(2):
        assert (await LiveReconciler(sessions, receipts).reconcile(uid, gateway, 0))['status'] == 'MATCHED'
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        fill = (await db.execute(select(LiveConfirmedFill))).scalar_one()
        assert account.cash == Decimal('89.75') and account.reserved_cash == 0
        assert fill.fee == Decimal('.25') and fill.cash_amount == 10
        assert not account.enabled  # Actual fee exceeded this fixture's zero fee budget.
