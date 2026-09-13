import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base
from app.models import RateLimitBucket
from app.auth import create_access_token, is_token_revoked, revoke_token
from app.services.security_state import DatabaseRateLimiter
from app.migrations import run_versioned_migrations, check_schema_completeness


@pytest.mark.asyncio
async def test_security_state_survives_new_engine_and_failed_request(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'security.db').as_posix()}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine)
    token = create_access_token(str(uuid.uuid4()))
    limiter = DatabaseRateLimiter('test', 1, 60, max_keys=2)
    async with session() as db:
        await limiter.check(db, 'a')
        await db.rollback()  # a rejected login cannot restore its quota
        await revoke_token(token, db)
    await engine.dispose()
    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine)() as db:
            assert await is_token_revoked(token, db)
            with pytest.raises(HTTPException) as exc:
                await DatabaseRateLimiter('test', 1, 60, max_keys=2).check(db, 'a')
            assert exc.value.status_code == 429
            await limiter.check(db, 'b')
            with pytest.raises(HTTPException):
                await limiter.check(db, 'c')  # capacity does not evict blocked keys
            await db.execute(delete(RateLimitBucket))
            await db.commit()
            await limiter.check(db, 'c')
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_readiness_rejects_stamped_but_missing_schema():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await run_versioned_migrations(conn)
            assert (await check_schema_completeness(conn))[0]
            await conn.execute(text('ALTER TABLE users DROP COLUMN role'))
            complete, _, detail = await check_schema_completeness(conn)
            assert not complete
            assert 'users.role' in detail
    finally:
        await engine.dispose()


def test_separate_logins_issue_distinct_tokens():
    uid = str(uuid.uuid4())
    assert create_access_token(uid) != create_access_token(uid)
