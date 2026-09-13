import uuid
from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import User, LiveWalletLink, LiveExecutionAccount, LiveReconciliation
from app.services import live_reconciliation_worker as worker

pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL port 55432')


@pytest.mark.asyncio
async def test_bad_credentials_disable_only_affected_account_and_continue(pg, monkeypatch):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    monkeypatch.setattr(worker, 'SessionLocal', sessions)
    reconcile = AsyncMock(return_value={'status': 'MATCHED'})
    monkeypatch.setattr(worker.LiveReconciler, 'reconcile', reconcile)
    def decrypt(value):
        if value == 'damaged':
            raise ValueError('fixture secret must not appear in durable error')
        return value
    monkeypatch.setattr(worker, 'decrypt_secret', decrypt)
    ids = [uuid.uuid4(), uuid.uuid4()]
    async with sessions() as db:
        for i, uid in enumerate(ids):
            wallet = '0x' + str(i+1) * 40
            db.add(User(id=uid, email=f'{uid}@worker.test'))
            await db.flush()
            db.add(LiveWalletLink(user_id=uid, polymarket_wallet_address=wallet, signer_address=wallet,
                signature_type=3, clob_api_key_enc='damaged' if i == 0 else 'key',
                clob_api_secret_enc='secret', clob_api_passphrase_enc='passphrase'))
            db.add(LiveExecutionAccount(user_id=uid, run_id=uuid.uuid4(), wallet_address=wallet,
                enabled=True, reconciled_at=datetime.utcnow(), cash=0, reserved_cash=0))
        await db.commit()
    await worker.reconcile_live_accounts()
    assert reconcile.await_count == 1 and reconcile.call_args.args[0] == ids[1]
    async with sessions() as db:
        bad = await db.get(LiveExecutionAccount, ids[0])
        good = await db.get(LiveExecutionAccount, ids[1])
        assert not bad.enabled and bad.reconciled_at is None
        assert good.enabled
        attempt = (await db.execute(select(LiveReconciliation))).scalar_one()
        assert attempt.status == 'BLOCKED' and 'fixture secret' not in attempt.detail


@pytest.mark.asyncio
async def test_credentials_cannot_rebind_existing_financial_journal(pg):
    from fastapi import HTTPException
    from app.api.live_trading import save_credentials, SaveCredentialsRequest
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    wallet = '0x' + '1' * 40
    async with sessions() as db:
        user = User(email=f'{uuid.uuid4()}@binding.test')
        db.add(user)
        await db.flush()
        link = LiveWalletLink(user_id=user.id, polymarket_wallet_address=wallet,
            signer_address=wallet, signature_type=0, clob_api_key_enc='original')
        db.add(link)
        db.add(LiveExecutionAccount(user_id=user.id, run_id=uuid.uuid4(), wallet_address=wallet,
                                   cash=100, reserved_cash=0, enabled=False))
        await db.commit()
        request = SaveCredentialsRequest(polymarket_wallet_address='0x'+'2'*40,
            clob_api_key='new-fixture-key', clob_api_secret='new-fixture-secret',
            clob_api_passphrase='new-fixture-passphrase')
        with pytest.raises(HTTPException) as exc:
            await save_credentials(request, user, db)
        assert exc.value.status_code == 409
        assert link.clob_api_key_enc == 'original' and link.polymarket_wallet_address == wallet
