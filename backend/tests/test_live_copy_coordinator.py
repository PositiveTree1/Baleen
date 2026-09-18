import copy
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
pytest.importorskip("polymarket")
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from eth_account import Account
from eth_account.messages import encode_typed_data
from polymarket._internal.actions.orders.types import UnsignedOrder
from polymarket._internal.actions.orders.typed_data import build_order_typed_data, build_order_signature
from polymarket._internal.actions.orders.orders import create_signed_order
from polymarket._internal.wallet import wrap_deposit_wallet_session_signer_signature
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import User, LiveExecutionAccount, LiveSigningSession, LiveCopyPolicy, CanonicalSourceEvent, LiveOrderIntent, LiveWalletBaseline
from app.services.live_copy_coordinator import LiveCopyCoordinator
from app.services.scoped_signer import ScopedOrderSigner
from app.services.live_risk import RiskRejected

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL')
WALLET, SOURCE = '0x'+'2'*40, '0x'+'3'*40
EXCHANGE = '0xe111180000d2663c0091e4f400237545b87b996b'
LIMITS = dict(max_order_cash='100', max_total_exposure='1000', max_token_exposure='500', max_daily_loss='10',
    max_open_orders=5, max_slippage_bps='100', max_quote_age_ms=10000, max_source_age_ms=60000, max_fee_bps='100')


async def setup(pg, fault=None):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    uid, run, source_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    session_key = Account.create()
    async with sessions() as db, db.begin():
        db.add(User(id=uid, email=f'{uid}@coordinator.test'))
        await db.flush()
        db.add(LiveExecutionAccount(user_id=uid, run_id=run, wallet_address=WALLET,
            cash=100, reserved_cash=0, enabled=True, reconciled_at=datetime.utcnow()))
        await db.flush()
        db.add(LiveWalletBaseline(user_id=uid, run_id=run, starting_cash=100, block_number=1,
            block_hash='0x'+'0'*64, block_time=datetime.utcnow()-timedelta(minutes=5),
            created_at=datetime.utcnow()-timedelta(seconds=10), observed_tokens=[]))
        db.add(LiveSigningSession(user_id=uid, wallet_address=WALLET, session_address=session_key.address.lower(), encrypted_key='fixture'))
        db.add(LiveCopyPolicy(user_id=uid, revision=1, source_wallets=[SOURCE], copy_ratio=1, limits=LIMITS,
            updated_at=datetime.utcnow()-timedelta(seconds=5)))
        db.add(CanonicalSourceEvent(id=source_id, chain_id=137, tx_hash='0x'+'a'*64,
            log_index=1, block_hash='0x'+'b'*64, block_time=datetime.utcnow(), source_wallet_address=SOURCE,
            condition_id='0x'+'c'*64, token_id='111', side='BUY', shares=100, price=.5, notional_usd=50,
            emitting_contract=EXCHANGE, status='CONFIRMED'))
    gateway = AsyncMock()
    gateway.credentials = SimpleNamespace(signer_address=session_key.address.lower(), api_key='fixture-api')
    owner = AsyncMock()
    owner.credentials = SimpleNamespace(signer_address='0x'+'4'*40)
    owner._get.return_value = {'wallet':WALLET,'signers':[{'address':session_key.address,
        'scopes':['CLOB'],'valid_until':int(time.time())+900}]}
    async def sign(**kw):
        unsigned = UnsignedOrder(chain_id=137, exchange_address=EXCHANGE, builder='0x'+'0'*64,
            expiration=kw['expiration'], maker=WALLET, maker_amount=int(kw['size']*kw['price']*1000000),
            metadata='0x'+'0'*64, order_type='GTD', salt=12345, side=kw['side'], signature_type=3,
            signer=WALLET, taker_amount=int(kw['size']*1000000), timestamp=int(time.time()*1000), token_id=kw['token_id'])
        signature = session_key.sign_message(encode_typed_data(full_message=build_order_typed_data(unsigned))).signature.hex()
        wrapped = wrap_deposit_wallet_session_signer_signature(session_key.address,
            build_order_signature(unsigned, '0x'+signature))
        if fault in ('policy', 'stop'):
            async with sessions() as db, db.begin():
                if fault == 'policy': (await db.get(LiveCopyPolicy, uid)).revision = 2
                if fault == 'stop': (await db.get(LiveExecutionAccount, uid)).enabled = False
        return create_signed_order(unsigned, wrapped, post_only=False)
    sdk = SimpleNamespace(wallet=WALLET, signer=session_key.address, wallet_type='DEPOSIT_WALLET', create_limit_order=AsyncMock(side_effect=sign))
    signer = ScopedOrderSigner(sdk, owner, gateway, wallet=WALLET, session_address=session_key.address)
    evidence = AsyncMock()
    evidence.source.return_value = {'quantity':Decimal(100), 'price':Decimal('.5')}
    observed = {'exchange':EXCHANGE,'accepting_orders':True,'fee_cap_bps':100,
        'book':{'asset_id':'111','timestamp':str(int(time.time()*1000)), 'tick_size':'.01', 'min_order_size':'1',
                'asks':[{'price':'.5','size':'200'}], 'bids':[{'price':'.49','size':'200'}]}}
    if fault == 'stale_quote':
        stale = copy.deepcopy(observed)
        stale['book']['timestamp'] = '1'
        evidence.market.side_effect = [observed, stale]
    else:
        evidence.market.return_value = observed
    async def submit(envelope, **kwargs):
        # Observe the durable SUBMITTING state before transport acknowledgement.
        async with sessions() as db:
            row = (await db.execute(select(LiveOrderIntent))).scalar_one()
            assert row.state == 'SUBMITTING'
            return {'success':True,'orderID':row.signed_order_hash}
    gateway.submit_signed_order.side_effect = submit
    runtime = SimpleNamespace(signer=signer, gateway=gateway)
    return sessions, uid, source_id, gateway, sdk, LiveCopyCoordinator(sessions, runtime, evidence)


@pytest.mark.asyncio
async def test_source_policy_signature_reservation_and_submission_are_connected_once(pg):
    sessions, uid, source_id, gateway, sdk, coordinator = await setup(pg)
    await coordinator.copy_source(uid, source_id)
    await pg.dispose()
    await coordinator.copy_source(uid, source_id)
    assert gateway.submit_signed_order.await_count == 1 and sdk.create_limit_order.await_count == 1
    async with sessions() as db:
        row = (await db.execute(select(LiveOrderIntent))).scalar_one()
        assert row.state == 'ACKNOWLEDGED' and row.risk_context['source_event_id'] == str(source_id)
        assert (await db.get(LiveExecutionAccount, uid)).reserved_cash == Decimal('50.5')


@pytest.mark.asyncio
async def test_statistics_reset_blocks_new_live_entry_before_signing(pg):
    from app.models import KeyValue
    from app.services.wallet_reset import GENERATION_KEY
    sessions, uid, source_id, gateway, sdk, coordinator = await setup(pg)
    async with sessions() as db, db.begin():
        db.add(KeyValue(key=GENERATION_KEY, value='fresh-generation'))
    with pytest.raises(RiskRejected, match='Fresh wallet research'):
        await coordinator.copy_source(uid, source_id)
    sdk.create_limit_order.assert_not_awaited()
    gateway.submit_signed_order.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['policy','stop','stale_quote'])
async def test_changed_conditions_never_post_a_prepared_order(pg, fault):
    sessions, uid, source_id, gateway, sdk, coordinator = await setup(pg, fault)
    with pytest.raises((RiskRejected, PermissionError)):
        await coordinator.copy_source(uid, source_id)
    gateway.submit_signed_order.assert_not_awaited()
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert account.cash == 100 and account.reserved_cash == 0


@pytest.mark.asyncio
async def test_source_before_policy_is_not_signed(pg):
    sessions, uid, source_id, gateway, sdk, coordinator = await setup(pg)
    async with sessions() as db, db.begin():
        (await db.get(LiveCopyPolicy, uid)).updated_at = datetime.utcnow()+timedelta(seconds=1)
    with pytest.raises(RiskRejected, match='predates'):
        await coordinator.copy_source(uid, source_id)
    sdk.create_limit_order.assert_not_awaited()
    gateway.submit_signed_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_enabled_account_without_verified_baseline_cannot_copy(pg):
    sessions, uid, source_id, gateway, sdk, coordinator = await setup(pg)
    async with sessions() as db, db.begin():
        await db.delete(await db.get(LiveWalletBaseline, uid))
    with pytest.raises(RiskRejected, match='baseline'):
        await coordinator.copy_source(uid, source_id)
    sdk.create_limit_order.assert_not_awaited()
    gateway.submit_signed_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_quantity_changed_during_signing_cannot_increase_allocation(pg):
    sessions, uid, source_id, gateway, sdk, coordinator = await setup(pg)
    coordinator.market_evidence.source.side_effect = [
        {'quantity':Decimal(100), 'price':Decimal('.5')},
        {'quantity':Decimal(50), 'price':Decimal('.5')}]
    with pytest.raises(RiskRejected, match='allocation'):
        await coordinator.copy_source(uid, source_id)
    gateway.submit_signed_order.assert_not_awaited()
    async with sessions() as db:
        assert (await db.get(LiveExecutionAccount, uid)).reserved_cash == 0
