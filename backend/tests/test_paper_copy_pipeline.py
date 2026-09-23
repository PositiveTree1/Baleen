import uuid
import time
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models import User, Wallet, WalletEvidence, CanonicalSourceEvent, PaperCopyAccount, PaperCopyResearchRun, PaperCopySniperAllocation, PaperCopyRosterRotation
from app.api.paper_copy import start_paper_copy, start_automatic_paper_copy, get_paper_copy, StartPaperCopy, StartAutomaticPaperCopy, selectable_wallets
from app.api.signals import watched_wallets
from app.services.paper_copy_worker import process_run
from app.services.paper_observation import book_quote
from app.services.paper_runs import archive_and_start
from app.services.settlement_receipts import PolygonSettlementReader
from app.services.sniper_allocator import process_standby_snipers
from app.services.roster_rotation import rotate_automatic_roster

ADDRESS = '0x'+'1'*40
ADDRESS_2 = '0x'+'2'*40
SNIPER = '0x'+'3'*40
ADDRESS_4 = '0x'+'4'*40
CONDITION = '0xcondition'


def book():
    return dict(asset_id='123', market=CONDITION, timestamp=str(int(time.time()*1000)),
                min_order_size='5', tick_size='.01', asks=[dict(price='.5', size='1000')], bids=[dict(price='.5', size='1000')])


def market():
    return dict(conditionId=CONDITION, clobTokenIds=['123'], acceptingOrders=True, closed=False,
                orderMinSize='1', feesEnabled=True, feeSchedule=dict(rate='.04', exponent=1, takerOnly=True))


@pytest.fixture
async def pipeline(monkeypatch):
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    user_id = uuid.uuid4()
    async with sessions() as db, db.begin():
        db.add(User(id=user_id, email='paper@example.test', sandbox_starting_balance_usd=100,
                    sandbox_balance_usd=100, sandbox_high_water_mark_usd=100))
        db.add(Wallet(address=ADDRESS, name='Test source', status='tracked'))
    monkeypatch.setattr('app.api.paper_copy.accounting_snapshot', AsyncMock(return_value={
        'status': 'observed', 'requested_wallet': ADDRESS, 'equity_usd': '1000',
        'valuation_time': datetime.utcnow().isoformat()+'Z'}))
    yield sessions, user_id
    await engine.dispose()


@pytest.mark.asyncio
async def test_selection_receipt_copy_dashboard_exit_and_reset(pipeline):
    sessions, uid = pipeline
    async with sessions() as db:
        user = await db.get(User, uid)
        result = await start_paper_copy(StartPaperCopy(wallets=[ADDRESS], starting_cash=100), user, db)
        assert result['status'] == 'ACTIVE'
        rid = result['runs'][0]['id']
        assert result['runs'][0]['policy']['ratio'] == '0.1'
        assert ADDRESS in await watched_wallets(db, True)
        # Cleared/unknown statistics must not hide the saved wallet from configuration.
        assert (await selectable_wallets('', user, db))[0]['address'] == ADDRESS
    client = AsyncMock()
    client.fetch_market_info.return_value = market()
    client.fetch_order_book.side_effect = lambda token: book()
    receipts = AsyncMock()
    receipts.source.return_value = {'quantity': Decimal(100), 'price': Decimal('.5'), 'cash_amount': Decimal(50)}
    async with sessions() as db, db.begin():
        db.add(CanonicalSourceEvent(id=uuid.uuid4(), source_wallet_address=ADDRESS, condition_id=CONDITION,
               token_id='123', side='BUY', shares=100, price=.5, notional_usd=50, block_time=datetime.utcnow()+timedelta(seconds=1),
               block_number=1, log_index=1, tx_hash='0xreceipt', block_hash='0xblock', emitting_contract='0xexchange', status='CONFIRMED'))
    # Move book time beyond the test source cutoff while preserving fresh quotes.
    async with sessions() as db, db.begin():
        source = (await db.execute(select(CanonicalSourceEvent))).scalars().one()
        source.block_time = datetime.utcnow()
    await process_run(sessions, rid, client, receipts)
    await process_run(sessions, rid, client, receipts)
    async with sessions() as db:
        user = await db.get(User, uid)
        state = await get_paper_copy(user, db)
        report = state['runs'][0]['report']
        assert state['runs'][0]['revision'] == 1
        assert report['events'][0]['status'] == 'filled'
        assert Decimal(report['cash']) == Decimal('94.90000')
        assert Decimal(report['valuation']['economic_pnl']) == Decimal('-.1')
    async with sessions() as db, db.begin():
        db.add(CanonicalSourceEvent(id=uuid.uuid4(), source_wallet_address=ADDRESS, condition_id=CONDITION,
            token_id='123', side='SELL', shares=60, price=.5, notional_usd=30,
            block_time=datetime.utcnow(), block_number=2, log_index=1, tx_hash='0xexit',
            block_hash='0xblock2', emitting_contract='0xexchange', status='CONFIRMED'))
    receipts.source.return_value = {'quantity': Decimal(60), 'price': Decimal('.5'), 'cash_amount': Decimal(30)}
    await process_run(sessions, rid, client, receipts)
    async with sessions() as db:
        user = await db.get(User, uid)
        state = await get_paper_copy(user, db)
        report = state['runs'][0]['report']
        assert report['positions'] == {'123':'4.0'}
        assert Decimal(report['cash']) == Decimal('97.84')
        assert Decimal(report['realized_pnl']) == Decimal('-.12')
        await archive_and_start(db, user, 200)
        await db.commit()
        assert (await get_paper_copy(user, db))['status'] == 'AWAITING_CONFIGURATION'
        assert ADDRESS not in await watched_wallets(db, True)
    await process_run(sessions, rid, client, receipts)
    async with sessions() as db:
        assert (await db.get(PaperCopyResearchRun, rid)).revision == 2


@pytest.mark.asyncio
async def test_failed_baseline_preserves_current_account_and_other_owner_isolation(pipeline, monkeypatch):
    sessions, uid = pipeline
    async with sessions() as db:
        user = await db.get(User, uid)
        await start_paper_copy(StartPaperCopy(wallets=[ADDRESS], starting_cash=100), user, db)
        original = user.active_paper_run_id
        monkeypatch.setattr('app.api.paper_copy.accounting_snapshot', AsyncMock(return_value={'status': 'unavailable'}))
        with pytest.raises(HTTPException):
            await start_paper_copy(StartPaperCopy(wallets=[ADDRESS], starting_cash=200), user, db)
        assert user.active_paper_run_id == original
        other = User(id=uuid.uuid4(), email='other@example.test')
        db.add(other)
        await db.flush()
        assert (await get_paper_copy(other, db))['status'] == 'NOT_CONFIGURED'


@pytest.mark.asyncio
async def test_automatic_roster_funds_ranked_active_wallets_and_exposes_standby_snipers(pipeline, monkeypatch):
    sessions, uid = pipeline
    from app.discovery.wallet_evidence import POLICY_VERSION
    def evidence(classification, pnl30, pnl7):
        return {'policy_version': POLICY_VERSION, 'generation': 'legacy', 'classification': classification,
                'reasons': ['LOW_OR_INTERMITTENT_ACTIVITY'] if classification == 'watchlist' else ['ACCOUNT_REPLAY_AND_FORWARD_VALIDATION_REQUIRED'],
                'metrics': {'economic_pnl': '75000', 'trade_pnl_30d': str(pnl30), 'trade_pnl_7d': str(pnl7),
                            'fills_per_day_30d': '1.5' if classification == 'watchlist' else '5', 'active_days_7d': 6}}
    async with sessions() as db, db.begin():
        db.add_all([Wallet(address=ADDRESS_2, name='Higher recent PnL', status='tracked'),
                    Wallet(address=SNIPER, name='Visible standby sniper', status='tracked')])
        db.add_all([WalletEvidence(wallet_address=ADDRESS, observed_at=datetime.utcnow(), payload=evidence('research_candidate', 100, 40)),
                    WalletEvidence(wallet_address=ADDRESS_2, observed_at=datetime.utcnow(), payload=evidence('research_candidate', 200, 10)),
                    WalletEvidence(wallet_address=SNIPER, observed_at=datetime.utcnow(), payload=evidence('watchlist', 50, 20))])
    async def snapshot(_, address):
        return {'status': 'observed', 'requested_wallet': address, 'equity_usd': '1000',
                'valuation_time': datetime.utcnow().isoformat()+'Z'}
    monkeypatch.setattr('app.api.paper_copy.accounting_snapshot', snapshot)
    async with sessions() as db:
        user = await db.get(User, uid)
        state = await start_automatic_paper_copy(StartAutomaticPaperCopy(starting_cash=300), user, db)
        assert state['selection_mode'] == 'automatic'
        assert [run['wallet'] for run in state['runs']] == [ADDRESS_2, ADDRESS]
        assert [sniper['address'] for sniper in state['standby_snipers']] == [SNIPER]
        assert state['roster_status']['active_eligible'] == 2
        assert state['roster_status']['standby'] == 1
        watched = await watched_wallets(db, True)
        assert {ADDRESS, ADDRESS_2, SNIPER}.issubset(set(watched))


@pytest.mark.asyncio
async def test_empty_automatic_roster_starts_discovery_without_archiving_current_run(pipeline, monkeypatch):
    sessions, uid = pipeline
    scheduled = False

    async def fake_discovery():
        nonlocal scheduled
        scheduled = True

    monkeypatch.setattr('app.workers.discovery_worker.run_discovery', fake_discovery)
    async with sessions() as db:
        user = await db.get(User, uid)
        with pytest.raises(HTTPException, match='fresh discovery scan has been started'):
            await start_automatic_paper_copy(StartAutomaticPaperCopy(starting_cash=100), user, db)
        await asyncio.sleep(0)
        state = await get_paper_copy(user, db)
        assert state['status'] == 'NOT_CONFIGURED'
        assert state['discovery']['status'] is not None
    assert scheduled


@pytest.mark.asyncio
async def test_automatic_rotation_retires_old_roster_when_policy_reaudit_has_no_replacement(pipeline, monkeypatch):
    """Old automatic sleeves must not keep buying after their policy expires."""
    sessions, uid = pipeline
    from app.discovery.wallet_evidence import POLICY_VERSION
    payload = {'policy_version': POLICY_VERSION, 'generation': 'legacy', 'classification': 'research_candidate',
               'reasons': ['ACCOUNT_REPLAY_AND_FORWARD_VALIDATION_REQUIRED'],
               'metrics': {'economic_pnl': '75000', 'trade_pnl_30d': '100', 'trade_pnl_7d': '40',
                           'fills_per_day_30d': '5', 'active_days_7d': 6}}
    async with sessions() as db, db.begin():
        db.add(WalletEvidence(wallet_address=ADDRESS, observed_at=datetime.utcnow(), payload=payload))
    async with sessions() as db:
        user = await db.get(User, uid)
        state = await start_automatic_paper_copy(StartAutomaticPaperCopy(starting_cash=100), user, db)
        run_id = state['runs'][0]['id']
        evidence = await db.get(WalletEvidence, ADDRESS)
        evidence.payload = {**payload, 'policy_version': 'superseded-policy'}
        await db.commit()
    result = await rotate_automatic_roster(sessions, uid, AsyncMock())
    assert result['promoted'] == []
    assert [row['wallet'] for row in result['retired']] == [ADDRESS]
    async with sessions() as db:
        assert (await db.get(PaperCopyResearchRun, run_id)).policy['role'] == 'retired'


@pytest.mark.asyncio
async def test_verified_standby_sniper_uses_only_free_cash_from_weakest_active_sleeve(pipeline, monkeypatch):
    sessions, uid = pipeline
    from app.discovery.wallet_evidence import POLICY_VERSION
    async with sessions() as db:
        user = await db.get(User, uid)
        await start_paper_copy(StartPaperCopy(wallets=[ADDRESS], starting_cash=100), user, db)
        db.add(Wallet(address=SNIPER, name='Standby', status='tracked'))
        db.add(WalletEvidence(wallet_address=SNIPER, observed_at=datetime.utcnow(), payload={
            'policy_version': POLICY_VERSION, 'generation': 'legacy', 'classification': 'watchlist',
            'reasons': ['LOW_OR_INTERMITTENT_ACTIVITY'], 'metrics': {'economic_pnl': '90000', 'trade_pnl_30d': '200',
            'trade_pnl_7d': '50', 'fills_per_day_30d': '1.5', 'active_days_7d': 6}}))
        db.add(CanonicalSourceEvent(id=uuid.uuid4(), source_wallet_address=SNIPER, condition_id=CONDITION,
            token_id='123', side='BUY', shares=200, price=.5, notional_usd=100,
            block_time=datetime.utcnow()+timedelta(seconds=1), block_number=10, log_index=1,
            tx_hash='0xsniper', block_hash='0xsniperblock', emitting_contract='0xexchange', status='CONFIRMED'))
        await db.commit()
    monkeypatch.setattr('app.services.sniper_allocator.accounting_snapshot', AsyncMock(return_value={
        'status': 'observed', 'requested_wallet': SNIPER, 'equity_usd': '1000',
        'valuation_time': datetime.utcnow().isoformat()+'Z'}))
    receipts = AsyncMock()
    receipts.source.return_value = {'quantity': Decimal(200), 'price': Decimal('.5'), 'cash_amount': Decimal(100)}
    await process_standby_snipers(sessions, uid, AsyncMock(), receipts)
    async with sessions() as db:
        allocation = (await db.execute(select(PaperCopySniperAllocation))).scalar_one()
        assert allocation.status == 'ALLOCATED'
        assert Decimal(allocation.allocated_cash_usd) == Decimal('10.00000')
        account = await db.get(PaperCopyAccount, uid)
        assert len(account.run_ids) == 2
        donor, sniper = (await db.execute(select(PaperCopyResearchRun).where(
            PaperCopyResearchRun.id.in_(account.run_ids)))).scalars().all()
        if sniper.source_wallet != SNIPER: donor, sniper = sniper, donor
        assert Decimal(donor.report['cash']) == Decimal('90.00000')
        assert sniper.policy['role'] == 'standby_sniper'
        assert sniper.policy['donor_run_id'] == donor.id


@pytest.mark.asyncio
async def test_automatic_revaluation_rotates_free_cash_without_closing_old_positions(pipeline, monkeypatch):
    sessions, uid = pipeline
    from app.discovery.wallet_evidence import POLICY_VERSION
    def evidence(classification, pnl30):
        return {'policy_version': POLICY_VERSION, 'generation': 'legacy', 'classification': classification,
                'reasons': ['CURRENT'] if classification == 'research_candidate' else ['EXCLUDED'],
                'metrics': {'economic_pnl': '80000', 'trade_pnl_30d': str(pnl30), 'trade_pnl_7d': '25',
                            'fills_per_day_30d': '5', 'active_days_7d': 6}}
    async with sessions() as db, db.begin():
        db.add_all([Wallet(address=ADDRESS_2, status='tracked'), Wallet(address=ADDRESS_4, status='tracked')])
        db.add_all([WalletEvidence(wallet_address=ADDRESS, observed_at=datetime.utcnow(), payload=evidence('research_candidate', 100)),
                    WalletEvidence(wallet_address=ADDRESS_2, observed_at=datetime.utcnow(), payload=evidence('research_candidate', 200)),
                    WalletEvidence(wallet_address=ADDRESS_4, observed_at=datetime.utcnow(), payload=evidence('needs_data', 300))])
    async def snapshot(_, address):
        return {'status': 'observed', 'requested_wallet': address, 'equity_usd': '1000',
                'valuation_time': datetime.utcnow().isoformat()+'Z'}
    monkeypatch.setattr('app.api.paper_copy.accounting_snapshot', snapshot)
    async with sessions() as db:
        user = await db.get(User, uid)
        await start_automatic_paper_copy(StartAutomaticPaperCopy(starting_cash=300), user, db)
        b = await db.get(WalletEvidence, ADDRESS_2)
        b.payload = evidence('excluded', 200)
        c = await db.get(WalletEvidence, ADDRESS_4)
        c.payload = evidence('research_candidate', 300)
        await db.commit()
    monkeypatch.setattr('app.services.roster_rotation.accounting_snapshot', snapshot)
    rotation = await rotate_automatic_roster(sessions, uid, AsyncMock())
    assert [row['wallet'] for row in rotation['promoted']] == [ADDRESS_4]
    async with sessions() as db:
        account = await db.get(PaperCopyAccount, uid)
        runs = (await db.execute(select(PaperCopyResearchRun).where(PaperCopyResearchRun.id.in_(account.run_ids)))).scalars().all()
        old = next(run for run in runs if run.source_wallet == ADDRESS_2)
        replacement = next(run for run in runs if run.source_wallet == ADDRESS_4)
        assert old.policy['role'] == 'retired'
        assert Decimal(old.report['cash']) == Decimal('0')
        assert replacement.policy['role'] == 'active'
        assert Decimal(replacement.policy['starting_cash']) == Decimal('150')
        assert (await db.execute(select(PaperCopyRosterRotation))).scalars().one().promoted[0]['wallet'] == ADDRESS_4


@pytest.mark.asyncio
async def test_retired_roster_wallet_blocks_new_buys_but_keeps_copied_inventory_exitable(pipeline):
    sessions, uid = pipeline
    stamp = datetime.utcnow()-timedelta(seconds=5)
    async with sessions() as db:
        user = await db.get(User, uid)
        state = await start_paper_copy(StartPaperCopy(wallets=[ADDRESS], starting_cash=100), user, db)
        run = await db.get(PaperCopyResearchRun, state['runs'][0]['id'])
        run.policy = {**run.policy, 'source_cutoff': str(datetime.utcnow().timestamp()-10)}
        db.add(CanonicalSourceEvent(id=uuid.uuid4(), source_wallet_address=ADDRESS, condition_id=CONDITION,
            token_id='123', side='BUY', shares=100, price=.5, notional_usd=50, block_time=stamp,
            block_number=1, log_index=1, tx_hash='0xentry', block_hash='0xb1', emitting_contract='0xexchange', status='CONFIRMED'))
        await db.commit()
    client, receipts = AsyncMock(), AsyncMock()
    client.fetch_market_info.return_value = market()
    client.fetch_order_book.side_effect = lambda token: book()
    receipts.source.return_value = {'quantity': Decimal(100), 'price': Decimal('.5'), 'cash_amount': Decimal(50)}
    await process_run(sessions, state['runs'][0]['id'], client, receipts)
    async with sessions() as db:
        run = await db.get(PaperCopyResearchRun, state['runs'][0]['id'])
        run.policy = {**run.policy, 'role': 'retired'}
        db.add_all([
                CanonicalSourceEvent(id=uuid.uuid4(), source_wallet_address=ADDRESS, condition_id=CONDITION,
                    token_id='123', side='BUY', shares=20, price=.5, notional_usd=10, block_time=stamp+timedelta(seconds=1),
                block_number=2, log_index=1, tx_hash='0xblocked', block_hash='0xb2', emitting_contract='0xexchange', status='CONFIRMED'),
                CanonicalSourceEvent(id=uuid.uuid4(), source_wallet_address=ADDRESS, condition_id=CONDITION,
                    token_id='123', side='SELL', shares=60, price=.5, notional_usd=30, block_time=stamp+timedelta(seconds=2),
                block_number=3, log_index=1, tx_hash='0xexit', block_hash='0xb3', emitting_contract='0xexchange', status='CONFIRMED')])
        await db.commit()
    receipts.source.side_effect = lambda source: {'quantity': Decimal(source.shares), 'price': Decimal('.5'),
                                                   'cash_amount': Decimal(source.notional_usd)}
    await process_run(sessions, state['runs'][0]['id'], client, receipts)
    async with sessions() as db:
        report = (await db.get(PaperCopyResearchRun, state['runs'][0]['id'])).report
        assert [event['status'] for event in report['events']] == ['filled', 'unavailable', 'filled'], report['events'][2].get('reason')
        assert report['positions'] == {'123': '4.0'}


@pytest.mark.parametrize('change,expected', [
    ({'timestamp': '1'}, 'stale'), ({'asset_id': 'wrong'}, 'identity'),
    ({'asks': [{'price': '.5', 'size': '1'}]}, 'depth')])
def test_quote_rejects_unusable_observations(change, expected):
    with pytest.raises(ValueError, match=expected):
        book_quote({**book(), **change}, market(), token='123', condition=CONDITION, side='BUY', quantity=Decimal(10), now_ms=int(time.time()*1000))


@pytest.mark.asyncio
async def test_real_receipt_verifier_feeds_paper_journal(pipeline):
    from tests.test_settlement_receipts import fixture_receipt, TX, BLOCK, EXCHANGE
    sessions, uid = pipeline
    stamp = int(time.time())
    async with sessions() as db:
        user = await db.get(User, uid)
        state = await start_paper_copy(StartPaperCopy(wallets=[ADDRESS], starting_cash=100), user, db)
        rid = state['runs'][0]['id']
        run = await db.get(PaperCopyResearchRun, rid)
        run.policy = {**run.policy, 'source_cutoff': str(stamp-1)}
        db.add(CanonicalSourceEvent(id=uuid.uuid4(), source_wallet_address=ADDRESS, condition_id=CONDITION,
            token_id='111', side='BUY', shares=100, price=.5, notional_usd=50,
            block_time=datetime.utcfromtimestamp(stamp), block_number=100, log_index=0,
            tx_hash=TX, block_hash=BLOCK, emitting_contract=EXCHANGE, status='CONFIRMED'))
        await db.commit()
    reader = PolygonSettlementReader(None)
    responses = {'eth_chainId': '0x89', 'eth_blockNumber': '0x100',
                 'eth_getTransactionReceipt': fixture_receipt(cash=50000000, qty=100000000),
                 'eth_getBlockByNumber': {'number': '0x64', 'hash': BLOCK, 'timestamp': hex(stamp)}}
    reader.rpc = AsyncMock(side_effect=lambda method, params: responses[method])
    client = AsyncMock()
    client.fetch_market_info.return_value = {**market(), 'clobTokenIds': ['111']}
    client.fetch_order_book.side_effect = lambda token: {**book(), 'asset_id': token}
    await process_run(sessions, rid, client, reader)
    async with sessions() as db:
        report = (await db.get(PaperCopyResearchRun, rid)).report
        assert report['events'][0]['status'] == 'filled'
        assert report['receipt_verification'] == 'canonical_polygon_receipts'
        assert report['positions'] == {'111': '10.0'}
