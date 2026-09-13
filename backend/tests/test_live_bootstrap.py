import uuid
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import User, LiveExecutionAccount, LiveSigningSession, LiveWalletBaseline
from app.services.live_bootstrap import LiveBootstrap

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL')


async def setup(pg):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    uid = uuid.uuid4()
    async with sessions() as db, db.begin():
        db.add(User(id=uid, email=f'{uid}@bootstrap.test', sandbox_balance_usd=10000))
        await db.flush()
        db.add(LiveSigningSession(user_id=uid, wallet_address='0x'+'1'*40, session_address='0x'+'2'*40,
            encrypted_key='fixture', verified_at=datetime.utcnow()))
    runtime = SimpleNamespace(signer=SimpleNamespace(session_address='0x'+'2'*40, verify_authorization=AsyncMock()),
                              gateway=AsyncMock(), owner_gateway=AsyncMock())
    runtime.gateway.open_orders.return_value = runtime.owner_gateway.open_orders.return_value = []
    runtime.owner_gateway.collateral_balance.return_value = {'balance':Decimal('137.654321')}
    reader = AsyncMock()
    reader.read.return_value = {'cash':Decimal('137.654321'), 'balances':{}, 'block_number':172,
        'block_hash':'0x'+'a'*64, 'block_time':datetime.utcnow()}
    return sessions, uid, runtime, reader, LiveBootstrap(sessions, runtime, reader)


@pytest.mark.asyncio
async def test_bootstrap_uses_real_cash_never_paper_seed_and_is_idempotent(pg):
    sessions, uid, runtime, reader, bootstrap = await setup(pg)
    result = await bootstrap.initialize(uid)
    assert result['startingCash'] == '137.654321' and not result['liveExecutionReady']
    await pg.dispose()
    assert (await bootstrap.initialize(uid))['runId'] == result['runId']
    assert reader.read.await_count == 1
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert account.cash == Decimal('137.654321') and account.reserved_cash == 0
        assert not account.enabled and account.reconciled_at is None
        assert (await db.get(LiveWalletBaseline, uid)).starting_cash == account.cash
        assert (await db.get(User, uid)).sandbox_balance_usd == 10000


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['positions','owner_orders','session_orders','cash','grant','revoked'])
async def test_bootstrap_never_imports_unproven_money_or_cost_basis(pg, fault):
    sessions, uid, runtime, reader, bootstrap = await setup(pg)
    if fault == 'positions': reader.read.return_value['balances'] = {'unknown-token':'20'}
    if fault == 'owner_orders': runtime.owner_gateway.open_orders.return_value = [{'id':'outside-order'}]
    if fault == 'session_orders': runtime.gateway.open_orders.return_value = [{'id':'outside-order'}]
    if fault == 'cash': runtime.owner_gateway.collateral_balance.return_value['balance'] = 138
    if fault == 'grant': runtime.signer.verify_authorization.side_effect = PermissionError('fixture revoked')
    if fault == 'revoked':
        async with sessions() as db, db.begin():
            (await db.get(LiveSigningSession, uid)).revoked_at = datetime.utcnow()
    with pytest.raises(PermissionError):
        await bootstrap.initialize(uid)
    async with sessions() as db:
        assert await db.get(LiveExecutionAccount, uid) is None
        assert await db.get(LiveWalletBaseline, uid) is None
