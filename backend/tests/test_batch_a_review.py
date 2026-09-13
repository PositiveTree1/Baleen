"""Independent Batch A regressions; all database and provider I/O is isolated."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app import migrations
from app.api.execution_logs import router
from app.auth import get_current_user_optional
from app.database import Base, get_db
from app.models import ExecutionLog, User


def test_rate_limit_identity_ignores_untrusted_forwarded_header():
    from starlette.requests import Request
    from app.api.users import _get_request_ip
    for spoofed in (b"1.1.1.1", b"2.2.2.2"):
        request = Request({"type": "http", "client": ("192.0.2.10", 1234),
                           "headers": [(b"x-forwarded-for", spoofed)]})
        assert _get_request_ip(request) == "192.0.2.10"


@pytest.mark.asyncio
async def test_failed_migration_is_not_recorded(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(migrations, "MIGRATIONS", [
        (1, "broken", ["ALTER TABLE missing_table ADD COLUMN value TEXT"], []),
    ])
    try:
        async with engine.begin() as conn:
            with pytest.raises(Exception):
                await migrations.run_versioned_migrations(conn)
            assert (await conn.execute(text("SELECT count(*) FROM schema_migrations"))).scalar() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_existing_column_does_not_hide_later_migration_steps(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(migrations, "MIGRATIONS", [
        (1, "upgrade", ["ALTER TABLE sample ADD COLUMN existing TEXT",
                        "ALTER TABLE sample ADD COLUMN added TEXT"], []),
    ])
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE sample (existing TEXT)"))
            assert await migrations.run_versioned_migrations(conn) == 1
            assert await migrations.run_versioned_migrations(conn) == 1
            columns = (await conn.execute(text("PRAGMA table_info(sample)"))).fetchall()
            assert {row[1] for row in columns} == {"existing", "added"}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_chart_ownership_and_no_fabricated_history(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    owner = User(id=uuid.uuid4(), email="owner@example.test", is_admin=False, role="user")
    stranger = User(id=uuid.uuid4(), email="stranger@example.test", is_admin=False, role="user")
    admin = User(id=uuid.uuid4(), email="admin@example.test", is_admin=True, role="admin")
    trade = ExecutionLog(id=uuid.uuid4(), user_id=owner.id, market_condition_id="private-condition",
                         market_question="Private trade", side="BUY", user_fill_price=0.4,
                         status="FILLED", executed_at=datetime.utcnow())
    api = FastAPI()
    api.include_router(router)
    async def db_override():
        async with sessions() as db:
            yield db
    api.dependency_overrides[get_db] = db_override
    from app.discovery.polymarket_client import PolymarketClient
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(PolymarketClient, "get_token_id_for_condition", lookup)
    monkeypatch.setattr("app.api.execution_logs.get_live_price", lambda *a, **kw: 0.4)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add_all([owner, stranger, admin, trade])
            await db.commit()
        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            for identity, expected in [(None, 401), (stranger, 403), (owner, 200), (admin, 200)]:
                async def identity_override():
                    return identity
                api.dependency_overrides[get_current_user_optional] = identity_override
                response = await client.get(f"/api/executions/{trade.id}/chart")
                assert response.status_code == expected
                if expected == 200:
                    points = response.json()["history"]
                    assert len(points) <= 2
                    assert all(p["price"] == 0.4 for p in points)
            # Legacy condition lookup must never select another account's trade.
            api.dependency_overrides[get_current_user_optional] = lambda: stranger
            response = await client.get("/api/executions/private-condition/chart")
            assert response.status_code in (403, 404)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_token_revocation_on_logout():
    from app.auth import create_access_token, is_token_revoked, revoke_token, get_current_user
    from app.api.users import router as users_router
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    user = User(id=user_id, email="revokeme@example.test", password_hash="hash", is_admin=False, role="user")
    
    api = FastAPI()
    api.include_router(users_router)
    
    async def db_override():
        async with sessions() as db:
            yield db
            
    api.dependency_overrides[get_db] = db_override
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add(user)
            await db.commit()
            
        token = create_access_token(str(user_id))
        async with sessions() as db:
            assert await is_token_revoked(token, db) is False
        
        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            # 1. Protected endpoint works before logout
            resp = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            
            # 2. Call logout
            resp_logout = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
            assert resp_logout.status_code == 200
            assert resp_logout.json()["status"] == "ok"
            async with sessions() as db:
                assert await is_token_revoked(token, db) is True
            
            # 3. Protected endpoint now rejects with 401
            resp_after = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
            assert resp_after.status_code == 401
            assert "revoked" in resp_after.json()["detail"].lower()
    finally:
        await engine.dispose()


