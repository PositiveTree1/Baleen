import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
from app.database import Base
from app.models import User, LiveWalletLink
from app.auth import encrypt_secret, decrypt_secret, _cipher_from_secret
from app.services.credential_rotation import (
    scan_and_inventory_credentials,
    rotate_and_reencrypt_credentials,
    verify_all_credentials_decryptable
)

@pytest.mark.asyncio
async def test_full_credential_rotation_and_retirement_lifecycle(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    
    key_alpha = "initial_secret_key_alpha_32bytes_long!"
    key_beta = "secondary_secret_key_beta_32bytes_long!"
    
    # 1. Start with Key Alpha as primary
    monkeypatch.setattr(settings, "SETTINGS_ENCRYPTION_KEY", key_alpha)
    monkeypatch.setattr(settings, "SETTINGS_ENCRYPTION_KEY_PREVIOUS", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    
    user_id = uuid.uuid4()
    raw_key = "polymarket_clob_api_key_123"
    raw_secret = "polymarket_clob_secret_456"
    raw_pass = "polymarket_clob_passphrase_789"
    
    enc_key_alpha = encrypt_secret(raw_key)
    enc_secret_alpha = encrypt_secret(raw_secret)
    enc_pass_alpha = encrypt_secret(raw_pass)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with sessions() as db:
        user = User(id=user_id, email="trader@test.local", password_hash="hash")
        link = LiveWalletLink(
            user_id=user_id,
            provider="magic",
            provider_user_id="prov_123",
            polymarket_wallet_address="0x1111111111111111111111111111111111111111",
            clob_api_key_enc=enc_key_alpha,
            clob_api_secret_enc=enc_secret_alpha,
            clob_api_passphrase_enc=enc_pass_alpha
        )
        db.add_all([user, link])
        await db.commit()
        
    # 2. Key rotation: Key Beta is now primary, Key Alpha is previous
    settings.SETTINGS_ENCRYPTION_KEY = key_beta
    settings.SETTINGS_ENCRYPTION_KEY_PREVIOUS = key_alpha
    
    # 3. Inventory: credentials encrypted under Alpha need re-encryption
    async with sessions() as db:
        inv = await scan_and_inventory_credentials(db)
        assert inv["total_wallet_links"] == 1
        assert inv["needs_reencryption_count"] == 3
        assert inv["current_key_count"] == 0
        
        # 4. Re-encrypt all credentials with Key Beta
        res = await rotate_and_reencrypt_credentials(db)
        assert res["reencrypted"] == 3
        assert res["failed"] == 0
        
    # 5. Retire Key Alpha completely (no previous key configured)
    settings.SETTINGS_ENCRYPTION_KEY_PREVIOUS = ""
    
    # 6. Verify all credentials can still be decrypted with Key Beta alone
    async with sessions() as db:
        all_ok = await verify_all_credentials_decryptable(db)
        assert all_ok is True
        
        inv_after = await scan_and_inventory_credentials(db)
        assert inv_after["current_key_count"] == 3
        assert inv_after["needs_reencryption_count"] == 0
        
        # Decrypt individual values to ensure exact plaintext fidelity
        stmt = await db.execute(Base.metadata.tables["live_wallet_links"].select().where(Base.metadata.tables["live_wallet_links"].c.user_id == str(user_id)))
        row = stmt.fetchone()
        assert decrypt_secret(row.clob_api_key_enc) == raw_key
        assert decrypt_secret(row.clob_api_secret_enc) == raw_secret
        assert decrypt_secret(row.clob_api_passphrase_enc) == raw_pass
        
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('unreadable', ['legacy-plaintext', 'v1:corrupt-token'])
async def test_rotation_aborts_atomically_and_plaintext_requires_opt_in(monkeypatch, unreadable):
    monkeypatch.setattr(settings, 'ENVIRONMENT', 'production')
    monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY', 'new-review-key')
    monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY_PREVIOUS', 'old-review-key')
    old = 'v1:' + _cipher_from_secret('old-review-key').encrypt(b'old-secret').decode()
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            uid = uuid.uuid4()
            db.add(User(id=uid, email='rotation-fixture@example.test'))
            db.add(LiveWalletLink(user_id=uid, clob_api_key_enc=old, clob_api_secret_enc=unreadable))
            await db.commit()
            with pytest.raises(ValueError, match='no changes committed'):
                await rotate_and_reencrypt_credentials(db)
        async with sessions() as db:
            from sqlalchemy import select
            link = (await db.execute(select(LiveWalletLink))).scalar_one()
            assert link.clob_api_key_enc == old
            assert link.clob_api_secret_enc == unreadable
            if unreadable == 'legacy-plaintext':
                result = await rotate_and_reencrypt_credentials(db, migrate_plaintext=True)
                assert result == {'reencrypted': 2, 'failed': 0}
                monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY_PREVIOUS', '')
                assert decrypt_secret(link.clob_api_key_enc) == 'old-secret'
                assert decrypt_secret(link.clob_api_secret_enc) == unreadable
            else:
                with pytest.raises(ValueError):
                    await rotate_and_reencrypt_credentials(db, migrate_plaintext=True)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('plaintext', [False, True])
async def test_session_keys_rotate_and_plaintext_keys_abort_even_with_migration_opt_in(monkeypatch, plaintext):
    from app.models import LiveSigningSession
    monkeypatch.setattr(settings, 'ENVIRONMENT', 'production')
    monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY', 'session-new-review-key')
    monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY_PREVIOUS', 'session-old-review-key')
    old = 'v1:' + _cipher_from_secret('session-old-review-key').encrypt(b'synthetic-session-material').decode()
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        uid = uuid.uuid4()
        async with sessions() as db, db.begin():
            db.add(User(id=uid, email='session-rotation@example.test'))
            db.add(LiveSigningSession(user_id=uid, wallet_address='0x'+'1'*40, session_address='0x'+'2'*40,
                encrypted_key='synthetic-session-material' if plaintext else old))
        async with sessions() as db:
            inv = await scan_and_inventory_credentials(db)
            assert inv['total_signing_sessions'] == 1
            if plaintext:
                assert inv['unrecoverable_count'] == 1
                assert not await verify_all_credentials_decryptable(db)
                with pytest.raises(ValueError, match='no changes committed'):
                    await rotate_and_reencrypt_credentials(db, migrate_plaintext=True)
            else:
                assert inv['needs_reencryption_count'] == 1
                assert (await rotate_and_reencrypt_credentials(db))['reencrypted'] == 1
                monkeypatch.setattr(settings, 'SETTINGS_ENCRYPTION_KEY_PREVIOUS', '')
                assert await verify_all_credentials_decryptable(db)
                assert decrypt_secret((await db.get(LiveSigningSession, uid)).encrypted_key) == 'synthetic-session-material'
    finally:
        await engine.dispose()
