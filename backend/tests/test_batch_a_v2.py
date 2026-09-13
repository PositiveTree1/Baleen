import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete, text

from app.main import app
from app.database import SessionLocal, init_db, engine
from app.models import User, ExecutionLog
from app.auth import (
    hash_password,
    create_access_token,
    encrypt_secret,
    decrypt_secret,
)
from app.config import settings
from app.migrations import run_versioned_migrations
from app.api.users import user_to_response


@pytest.fixture(autouse=True)
async def setup_batch_a_db():
    await init_db()
    yield
    async with SessionLocal() as db:
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(User).where(User.email.like("%@batchatest.io")))
        await db.commit()


@pytest.mark.asyncio
async def test_versioned_migrations_track_schema():
    """Verify migrations track schema version and run idempotently."""
    async with engine.begin() as conn:
        version = await run_versioned_migrations(conn)
        assert version >= 5
        res = await conn.execute(text("SELECT MAX(version) FROM schema_migrations"))
        current_v = res.scalar()
        assert current_v == version


@pytest.mark.asyncio
async def test_key_rotation_support():
    """Verify encryption key rotation with fallback to previous key."""
    orig_key = settings.SETTINGS_ENCRYPTION_KEY
    orig_prev = settings.SETTINGS_ENCRYPTION_KEY_PREVIOUS
    try:
        settings.SETTINGS_ENCRYPTION_KEY = "old-signing-key-for-test-rotation-12345"
        old_ciphertext = encrypt_secret("my-polymarket-secret")
        assert old_ciphertext.startswith("v1:")

        # Now rotate the active key and set the old one as previous
        settings.SETTINGS_ENCRYPTION_KEY_PREVIOUS = "old-signing-key-for-test-rotation-12345"
        settings.SETTINGS_ENCRYPTION_KEY = "new-fresh-primary-key-67890-abcdefg"

        # Should successfully decrypt with previous key
        decrypted = decrypt_secret(old_ciphertext)
        assert decrypted == "my-polymarket-secret"
    finally:
        settings.SETTINGS_ENCRYPTION_KEY = orig_key
        settings.SETTINGS_ENCRYPTION_KEY_PREVIOUS = orig_prev


@pytest.mark.asyncio
async def test_auth_protection_on_private_endpoints():
    """Verify 401 for anonymous/invalid tokens and 403 for cross-account access."""
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    async with SessionLocal() as db:
        u1 = User(id=user1_id, email="u1@batchatest.io", password_hash=hash_password("p1"), role="user", is_admin=False)
        u2 = User(id=user2_id, email="u2@batchatest.io", password_hash=hash_password("p2"), role="user", is_admin=False)
        u_admin = User(id=admin_id, email="admin@batchatest.io", password_hash=hash_password("pa"), role="admin", is_admin=True)
        db.add_all([u1, u2, u_admin])
        await db.commit()

    token1 = create_access_token(str(user1_id), role="user")
    token2 = create_access_token(str(user2_id), role="user")
    token_admin = create_access_token(str(admin_id), role="admin")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Private Executions Read
        # Anonymous -> 401
        r = await ac.get("/api/executions", params={"userId": str(user1_id)})
        assert r.status_code == 401

        # Invalid token -> 401
        r = await ac.get("/api/executions", params={"userId": str(user1_id)}, headers={"Authorization": "Bearer invalid.jwt.token"})
        assert r.status_code == 401

        # Cross-account user2 accessing user1 -> 403
        r = await ac.get("/api/executions", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403

        # Self access -> 200
        r = await ac.get("/api/executions", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token1}"})
        assert r.status_code == 200

        # Admin access -> 200
        r = await ac.get("/api/executions", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code == 200

        # 2. User Settings Read
        # Anonymous -> 401
        r = await ac.get(f"/api/users/{user1_id}")
        assert r.status_code == 401

        # Cross-account -> 403
        r = await ac.get(f"/api/users/{user1_id}", headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403

        # Self access -> 200
        r = await ac.get(f"/api/users/{user1_id}", headers={"Authorization": f"Bearer {token1}"})
        assert r.status_code == 200

        # 3. Live Trading Credentials Write
        payload = {
            "user_id": str(user1_id),
            "polymarket_wallet_address": "0x1111111111111111111111111111111111111111",
            "clob_api_key": "testkey",
            "clob_api_secret": "testsec",
            "clob_api_passphrase": "testpass"
        }
        # Anonymous -> 401
        r = await ac.post("/api/live-trading/credentials", json=payload)
        assert r.status_code in (401, 403)

        # Cross-account -> 403
        r = await ac.post("/api/live-trading/credentials", json=payload, headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403

        # 4. Reset Sandbox
        # Anonymous -> 401
        r = await ac.post("/api/executions/reset-sandbox", params={"userId": str(user1_id)})
        assert r.status_code in (401, 403)

        # Cross-account -> 403
        r = await ac.post("/api/executions/reset-sandbox", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403

        # 5. Portfolio Summary (/api/executions/summary)
        # Anonymous with userId -> 401
        r = await ac.get("/api/executions/summary", params={"userId": str(user1_id)})
        assert r.status_code == 401

        # Cross-account -> 403
        r = await ac.get("/api/executions/summary", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403

        # Self access -> 200
        r = await ac.get("/api/executions/summary", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token1}"})
        assert r.status_code == 200

        # Admin access -> 200
        r = await ac.get("/api/executions/summary", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code == 200

        # Anonymous without userId -> 200 (Public benchmark)
        r = await ac.get("/api/executions/summary")
        assert r.status_code == 200

        # 6. Portfolio Snapshots (/api/executions/snapshots)
        # Anonymous with userId -> 401
        r = await ac.get("/api/executions/snapshots", params={"userId": str(user1_id)})
        assert r.status_code == 401

        # Cross-account -> 403
        r = await ac.get("/api/executions/snapshots", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403

        # Self access -> 200
        r = await ac.get("/api/executions/snapshots", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token1}"})
        assert r.status_code == 200

        # Admin access -> 200
        r = await ac.get("/api/executions/snapshots", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code == 200

        # Anonymous without userId -> 200 (Public benchmark)
        r = await ac.get("/api/executions/snapshots")
        assert r.status_code == 200

        # 7. Copied Wallet Stats (/api/wallets/copied-stats)
        # Anonymous with userId -> 401
        r = await ac.get("/api/wallets/copied-stats", params={"userId": str(user1_id)})
        assert r.status_code == 401

        # Cross-account -> 403
        r = await ac.get("/api/wallets/copied-stats", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403

        # Self access -> 200
        r = await ac.get("/api/wallets/copied-stats", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token1}"})
        assert r.status_code == 200

        # Admin access -> 200
        r = await ac.get("/api/wallets/copied-stats", params={"userId": str(user1_id)}, headers={"Authorization": f"Bearer {token_admin}"})
        assert r.status_code == 200

        # Anonymous without userId -> 200 (Public benchmark)
        r = await ac.get("/api/wallets/copied-stats")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_plaintext_credentials_rejected_in_production():
    """Verify legacy plaintext credentials are rejected in production."""
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        decrypted = decrypt_secret("raw-unencrypted-secret")
        assert decrypted is None

        settings.ENVIRONMENT = "development"
        decrypted_dev = decrypt_secret("raw-unencrypted-secret")
        assert decrypted_dev == "raw-unencrypted-secret"
    finally:
        settings.ENVIRONMENT = orig_env


@pytest.mark.asyncio
async def test_zero_balance_preserved():
    """Verify zero balance is not defaulted to 10000 in user_to_response."""
    u = User(id=uuid.uuid4(), email="zero@batchatest.io", sandbox_balance_usd=0.0, sandbox_starting_balance_usd=10000.0)
    resp = user_to_response(u)
    assert resp["currentBalance"] == 0.0


@pytest.mark.asyncio
async def test_copilot_payload_limit():
    """Verify per-message (4,000 chars) and aggregate (16,000 chars) limits on copilot chat."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Single message exceeding 4,000 chars is rejected by schema validator with 422
        oversized_single = "a" * 4500
        r_single = await ac.post("/api/copilot/chat", json={"messages": [{"role": "user", "content": oversized_single}]})
        assert r_single.status_code == 422

        # 2. Combined messages exceeding 16,000 chars is rejected by aggregate bound with 400
        messages = [{"role": "user", "content": "a" * 3500} for _ in range(5)]
        r_agg = await ac.post("/api/copilot/chat", json={"messages": messages})
        assert r_agg.status_code == 400
        assert "exceeds maximum allowed payload size" in r_agg.json().get("detail", "")

