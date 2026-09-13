import uuid
from datetime import datetime
from unittest.mock import AsyncMock
from eth_account import Account
from eth_account.messages import encode_typed_data
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import User, LiveSigningSession, LiveWalletLink, LiveSessionOperation
from app.services.session_authorization import SessionAuthorization, typed_data

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL')
WALLET = '0x'+'1'*40


async def setup(pg):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    owner, session = Account.create(), Account.create()
    uid = uuid.uuid4()
    async with sessions() as db, db.begin():
        db.add(User(id=uid, email=f'{uid}@owner-operation.test'))
        await db.flush()
        db.add(LiveSigningSession(user_id=uid, wallet_address=WALLET, session_address=session.address.lower(), encrypted_key='fixture'))
        db.add(LiveWalletLink(user_id=uid, polymarket_wallet_address=WALLET, signer_address=owner.address.lower(), signature_type=3))
    relay = AsyncMock()
    relay.nonce.return_value = str(2**200)
    relay.submit.return_value = {'status':'SUBMITTED', 'transactionId':'fixture-relay-id'}
    service = SessionAuthorization(sessions, relay, owner_check=AsyncMock())
    return sessions, owner, uid, relay, service


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['AUTHORIZE','REVOKE'])
async def test_owner_approves_exact_typed_challenge_and_post_is_durable_once(pg, kind):
    sessions, owner, uid, relay, service = await setup(pg)
    challenge = await service.prepare(uid, kind)
    assert challenge == await service.prepare(uid, kind)
    assert challenge['typedData']['message']['nonce'] == str(2**200)
    assert challenge['typedData']['message']['calls'][0]['value'] == '0'
    assert challenge['typedData']['message']['calls'][0]['target'].lower() == WALLET
    assert challenge['scopes'] == (['CLOB'] if kind == 'AUTHORIZE' else [])
    signature = '0x'+owner.sign_message(encode_typed_data(full_message=challenge['typedData'])).signature.hex()
    async def post(operation, sig):
        async with sessions() as db:
            assert (await db.get(LiveSessionOperation, operation.id)).state == 'SUBMITTING'
            session = await db.get(LiveSigningSession, uid)
            assert (session.revoked_at is not None) == (kind == 'REVOKE')
        return {'status':'SUBMITTED', 'transactionId':'fixture-relay-id'}
    relay.submit.side_effect = post
    oid = uuid.UUID(challenge['id'])
    submitted = await service.submit(uid, oid, signature)
    assert submitted['state'] == 'PENDING' and not submitted['liveExecutionReady']
    await pg.dispose()
    assert (await service.submit(uid, oid, signature))['state'] == 'PENDING'
    assert relay.submit.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['wrong_owner','wrong_scope','expired','disabled','other_user','timeout'])
async def test_invalid_or_uncertain_authorization_never_reposts(pg, fault):
    sessions, owner, uid, relay, service = await setup(pg)
    challenge = await service.prepare(uid, 'AUTHORIZE')
    oid = uuid.UUID(challenge['id'])
    signing = challenge['typedData']
    if fault == 'wrong_owner': owner = Account.create()
    if fault == 'wrong_scope': signing['message']['calls'][0]['value'] = '1'
    signature = '0x'+owner.sign_message(encode_typed_data(full_message=signing)).signature.hex()
    async with sessions() as db, db.begin():
        if fault == 'expired': (await db.get(LiveSessionOperation, oid)).deadline = 1
        if fault == 'disabled': (await db.get(LiveSigningSession, uid)).revoked_at = datetime.utcnow()
    if fault == 'timeout': relay.submit.side_effect = TimeoutError('synthetic fixture timeout')
    with pytest.raises(PermissionError):
        await service.submit(uuid.uuid4() if fault == 'other_user' else uid, oid, signature)
    if fault == 'timeout':
        await pg.dispose()
        assert (await service.submit(uid, oid, signature))['state'] == 'UNKNOWN'
        assert (await service.prepare(uid, 'AUTHORIZE'))['id'] == str(oid)
        assert relay.submit.await_count == 1
    else:
        relay.submit.assert_not_awaited()
