"""Isolated setup API and account-bound session custody tests. No live calls."""
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from eth_account import Account
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.api import live_setup
from app.auth import encrypt_secret, get_current_user
from app.config import settings
from app.database import Base, get_db
from app.models import User, LiveSigningSession, LiveWalletLink, LiveCopyPolicy, LiveExecutionAccount
from app.services.live_runtime import decode_session_key

WALLET = '0x'+'1'*40


@pytest.fixture
async def api(monkeypatch):
    monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY', 'setup-test-encryption-key')
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    user = User(id=uuid.uuid4(), email='setup@example.test')
    async with sessions() as db, db.begin():
        db.add(user)
        db.add(LiveWalletLink(user_id=user.id, signature_type=3, signer_address='0x'+'2'*40,
            polymarket_wallet_address=WALLET))
    app = FastAPI()
    app.include_router(live_setup.router)
    async def session():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr(live_setup, 'verify_owner_wallet', AsyncMock())
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client, sessions, user
    await engine.dispose()


@pytest.mark.asyncio
async def test_prepare_is_idempotent_returns_no_key_and_requires_owner_grant(api):
    client, sessions, user = api
    assert (await client.get('/api/live-trading/session')).json()['status'] == 'not_configured'
    first = (await client.post('/api/live-trading/session')).json()
    assert first == (await client.post('/api/live-trading/session')).json()
    assert first['ownerAuthorizationRequired'] and not first['liveExecutionReady']
    async with sessions() as db:
        row = await db.get(LiveSigningSession, user.id)
        key = decode_session_key(row)
        assert key not in json.dumps(first) and row.encrypted_key not in json.dumps(first)
        assert Account.from_key(key).address.lower() == first['sessionAddress']
    result = (await client.post('/api/live-trading/session/disable')).json()
    assert result['localSigningDisabled'] and result['ownerRevocationRequired']
    async with sessions() as db:
        with pytest.raises(PermissionError):
            decode_session_key(await db.get(LiveSigningSession, user.id))


@pytest.mark.asyncio
async def test_unknown_wallet_owner_cannot_reserve_wallet_session(api, monkeypatch):
    client, sessions, user = api
    monkeypatch.setattr(live_setup, 'verify_owner_wallet', AsyncMock(side_effect=PermissionError('synthetic-secret')))
    response = await client.post('/api/live-trading/session')
    assert response.status_code == 409 and 'synthetic-secret' not in response.text
    async with sessions() as db:
        assert await db.get(LiveSigningSession, user.id) is None


@pytest.mark.asyncio
async def test_verify_does_not_override_a_concurrent_disable(api, monkeypatch):
    client, sessions, user = api
    address = (await client.post('/api/live-trading/session')).json()['sessionAddress']
    @asynccontextmanager
    async def runtime(*args):
        async with sessions() as db, db.begin():
            (await db.get(LiveSigningSession, user.id)).revoked_at = datetime.utcnow()
        yield SimpleNamespace(signer=SimpleNamespace(session_address=address,
            verify_authorization=AsyncMock(return_value=2000000000)))
    monkeypatch.setattr(live_setup, 'live_runtime', runtime)
    assert (await client.post('/api/live-trading/session/verify')).status_code == 409
    async with sessions() as db:
        row = await db.get(LiveSigningSession, user.id)
        assert row.revoked_at is not None and row.verified_at is None


@pytest.mark.asyncio
async def test_session_wallet_cannot_be_rebound_by_credentials_form(api):
    from app.api.live_trading import save_credentials, SaveCredentialsRequest
    from fastapi import HTTPException
    client, sessions, user = api
    await client.post('/api/live-trading/session')
    async with sessions() as db:
        with pytest.raises(HTTPException) as error:
            await save_credentials(SaveCredentialsRequest(polymarket_wallet_address='0x'+'9'*40,
                clob_api_key='fixture', clob_api_secret='fixture', clob_api_passphrase='fixture'), user, db)
        assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_policy_is_explicit_stops_account_and_has_no_cross_user_effect(api):
    client, sessions, user = api
    from tests.test_live_copy_coordinator import LIMITS
    payload = {**LIMITS, 'source_wallets':['0x'+'3'*40], 'copy_ratio':'.1'}
    async with sessions() as db, db.begin():
        db.add(LiveExecutionAccount(user_id=user.id, run_id=uuid.uuid4(), wallet_address=WALLET,
            cash=35, reserved_cash=2, enabled=True))
    assert (await client.get('/api/live-trading/copy-policy')).json() is None
    result = await client.put('/api/live-trading/copy-policy', json=payload)
    assert result.status_code == 200 and result.json()['revision'] == 1
    assert result.json()['requiresReactivation']
    assert (await client.put('/api/live-trading/copy-policy', json=payload)).json()['revision'] == 2
    async with sessions() as db:
        account = await db.get(LiveExecutionAccount, user.id)
        assert not account.enabled and account.cash == 35 and account.reserved_cash == 2
        assert await db.get(LiveCopyPolicy, uuid.uuid4()) is None
    for wrong in ({'copy_ratio':'NaN'}, {'max_open_orders':True}, {'source_wallets':['bad']},
                  {'source_wallets':payload['source_wallets']*2}, {'max_order_cash':'0'}):
        assert (await client.put('/api/live-trading/copy-policy', json={**payload, **wrong})).status_code == 422


@pytest.mark.parametrize('fault', ['user', 'wallet', 'purpose', 'identity', 'plaintext', 'revoked'])
def test_session_material_cannot_be_rebound_or_used_after_revocation(monkeypatch, fault):
    monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY', 'setup-test-encryption-key')
    key, uid = Account.create(), uuid.uuid4()
    payload = {'purpose':'baleen-clob-session', 'user_id':str(uid), 'wallet':WALLET, 'key':key.key.hex()}
    if fault in ('user','wallet','purpose'):
        payload[{'user':'user_id','wallet':'wallet','purpose':'purpose'}[fault]] = 'wrong'
    row = SimpleNamespace(user_id=uid, wallet_address=WALLET, session_address=key.address.lower(),
        revoked_at=datetime.utcnow() if fault == 'revoked' else None,
        encrypted_key=json.dumps(payload) if fault == 'plaintext' else encrypt_secret(json.dumps(payload)))
    if fault == 'identity': row.session_address = '0x'+'5'*40
    with pytest.raises(PermissionError):
        decode_session_key(row)


@pytest.mark.asyncio
async def test_copy_ratio_cannot_change_while_source_inventory_remains(api):
    client, sessions, user = api
    from app.models import LiveSourcePosition
    from tests.test_live_copy_coordinator import LIMITS
    from decimal import Decimal
    source = '0x'+'3'*40
    payload = {**LIMITS, 'source_wallets':[source], 'copy_ratio':'.5'}
    async with sessions() as db, db.begin():
        db.add(LiveExecutionAccount(user_id=user.id, run_id=uuid.uuid4(), wallet_address=WALLET,
            cash=35, reserved_cash=0, enabled=True))
    assert (await client.put('/api/live-trading/copy-policy', json=payload)).status_code == 200
    async with sessions() as db, db.begin():
        db.add(LiveSourcePosition(user_id=user.id, source_wallet_address=source, token_id='123', quantity=10))
    changed = await client.put('/api/live-trading/copy-policy', json={**payload, 'copy_ratio':'.2'})
    assert changed.status_code == 409
    async with sessions() as db:
        assert (await db.get(LiveCopyPolicy, user.id)).copy_ratio == Decimal('.5')
    assert (await client.put('/api/live-trading/copy-policy', json=payload)).status_code == 200
