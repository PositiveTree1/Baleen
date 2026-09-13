"""Opt-in local PostgreSQL integration. Never points at a user's application DB."""
import asyncio
import os
import uuid
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base
from app import migrations
from app.models import User
from app.auth import create_access_token, is_token_revoked, revoke_token
from app.services.security_state import DatabaseRateLimiter

URL = os.environ.get('BALEEN_TEST_POSTGRES_URL')
pytestmark = pytest.mark.skipif(not URL, reason='Requires isolated local PostgreSQL on port 55432')


@pytest_asyncio.fixture
async def pg():
    parsed = urlparse(URL)
    assert parsed.hostname in ('localhost', '127.0.0.1') and parsed.port == 55432
    schema = 'batch_a_' + uuid.uuid4().hex
    admin = create_async_engine(URL)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine = create_async_engine(URL, pool_size=2, max_overflow=0, pool_timeout=3,
                                 connect_args={'server_settings': {'search_path': schema}})
    try:
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        await admin.dispose()


async def initialize(engine):
    async with engine.begin() as conn:
        await conn.execute(text('SELECT pg_advisory_xact_lock(20260908, 1)'))
        await conn.run_sync(Base.metadata.create_all)
        return await migrations.run_versioned_migrations(conn)


@pytest.mark.asyncio
async def test_concurrent_cold_start_and_old_schema_upgrade(pg):
    assert await asyncio.gather(*(initialize(pg) for _ in range(4))) == [migrations.LATEST_SCHEMA_VERSION] * 4
    async with pg.begin() as conn:
        await conn.execute(text("INSERT INTO users (id, email) VALUES (:id, 'retained@example.test')"), {'id': uuid.uuid4()})
        await conn.execute(text('ALTER TABLE users DROP COLUMN role'))
        await conn.execute(text('ALTER TABLE users DROP COLUMN is_admin'))
        await conn.execute(text('DELETE FROM schema_migrations WHERE version >= 3'))
    await initialize(pg)
    async with pg.begin() as conn:
        assert (await migrations.check_schema_completeness(conn))[0]
        assert (await conn.execute(text("SELECT count(*) FROM users WHERE email = 'retained@example.test'"))).scalar_one() == 1


@pytest.mark.asyncio
async def test_postgres_ddl_and_version_rollback(pg, monkeypatch):
    await initialize(pg)
    broken = (99, 'injected_failure', [], ['CREATE TABLE rollback_probe (id INTEGER)', 'ALTER TABLE absent_table ADD COLUMN x INTEGER'])
    monkeypatch.setattr(migrations, 'MIGRATIONS', migrations.MIGRATIONS + [broken])
    with pytest.raises(Exception):
        async with pg.begin() as conn:
            await migrations.run_versioned_migrations(conn)
    async with pg.begin() as conn:
        assert (await conn.execute(text("SELECT to_regclass('rollback_probe')"))).scalar_one() is None
        assert (await conn.execute(text('SELECT count(*) FROM schema_migrations WHERE version = 99'))).scalar_one() == 0


@pytest.mark.asyncio
async def test_concurrent_limits_and_persistent_logout(pg):
    await initialize(pg)
    sessions = async_sessionmaker(pg)
    async def attempt():
        async with sessions() as db:
            try:
                await db.execute(text('SELECT 1'))  # auth already checked out a connection
                await DatabaseRateLimiter('parallel', 3, 60).check(db, 'same-client')
                return True
            except HTTPException as exc:
                assert exc.status_code == 429
                return False
    assert sum(await asyncio.gather(*(attempt() for _ in range(12)))) == 3
    token = create_access_token(str(uuid.uuid4()))
    async with sessions() as db:
        await revoke_token(token, db)
    await pg.dispose()  # force entirely new database connections
    async with sessions() as db:
        assert await is_token_revoked(token, db)


@pytest.mark.asyncio
async def test_guest_signup_creates_user_before_snapshot(pg):
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.api.users import router
    from app.database import get_db
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    api = FastAPI()
    api.include_router(router)
    async def db_override():
        async with sessions() as db:
            yield db
    api.dependency_overrides[get_db] = db_override
    async with AsyncClient(transport=ASGITransport(app=api), base_url='http://test') as client:
        response = await client.post('/api/auth/guest')
        assert response.status_code == 200
        data = response.json()
        auth = {'Authorization': 'Bearer ' + data['access_token']}
        assert (await client.get('/api/me', headers=auth)).status_code == 200
    async with sessions() as db:
        snapshot = (await db.execute(text('SELECT balance, total_pnl FROM portfolio_snapshots WHERE user_id = :id'),
                                     {'id': uuid.UUID(data['id'])})).one()
        assert snapshot == (10000, 0)
