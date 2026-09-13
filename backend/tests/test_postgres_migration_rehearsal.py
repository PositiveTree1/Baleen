import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app import migrations
from app.migrations import check_schema_completeness, run_versioned_migrations, LATEST_SCHEMA_VERSION
from app.database import Base, get_db
from app.main import app

@pytest.mark.asyncio
async def test_ready_endpoint_checks_schema_migration_completeness():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    
    async def db_override():
        async with sessions() as db:
            yield db
            
    app.dependency_overrides[get_db] = db_override
    try:
        # Step 1: Database without schema_migrations table returns 503
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/ready")
            assert resp.status_code == 503
            assert "Schema incomplete" in resp.json()["error"]
            
        # Step 2: Database with partial migrations (e.g. v2 < LATEST_SCHEMA_VERSION) returns 503
        async with engine.begin() as conn:
            await conn.execute(text(migrations.MIGRATION_TABLE_SQL_SQLITE))
            await conn.execute(text("INSERT INTO schema_migrations (version, name) VALUES (1, 'base_schema');"))
            await conn.execute(text("INSERT INTO schema_migrations (version, name) VALUES (2, 'metadata');"))
            
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/ready")
            assert resp.status_code == 503
            assert resp.json()["current_schema_version"] == 2
            assert resp.json()["required_schema_version"] == LATEST_SCHEMA_VERSION

        # Step 3: Fully migrated database returns 200 ready
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await run_versioned_migrations(conn)
            
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/ready")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ready"
            assert resp.json()["schema_version"] == LATEST_SCHEMA_VERSION
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()

@pytest.mark.asyncio
async def test_old_schema_incremental_upgrade_rehearsal():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # Create old base schema v1
            await conn.execute(text("CREATE TABLE wallets (address TEXT PRIMARY KEY, status TEXT, tier TEXT);"))
            await conn.execute(text("CREATE TABLE execution_logs (id TEXT PRIMARY KEY, user_id TEXT, market_condition_id TEXT, status TEXT);"))
            await conn.execute(text("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT);"))
            await conn.execute(text("CREATE TABLE live_wallet_links (user_id TEXT PRIMARY KEY);"))
            await conn.execute(text("CREATE TABLE portfolio_snapshots (id TEXT PRIMARY KEY, user_id TEXT, timestamp TIMESTAMP);"))
            # SandboxRun was already part of the base ORM schema before v12.
            await conn.execute(text("CREATE TABLE sandbox_runs (id TEXT PRIMARY KEY, status TEXT);"))
            
            # Apply all versioned migrations
            final_version = await run_versioned_migrations(conn)
            assert final_version == LATEST_SCHEMA_VERSION
            
            # Verify columns added by migrations exist
            wallet_cols = {row[1] for row in (await conn.execute(text("PRAGMA table_info(wallets);"))).fetchall()}
            assert "pseudonym" in wallet_cols
            assert "profile_image" in wallet_cols
            
            exec_cols = {row[1] for row in (await conn.execute(text("PRAGMA table_info(execution_logs);"))).fetchall()}
            assert "fee_usd" in exec_cols
            assert "resolution_outcome" in exec_cols
            assert "realized_pnl_usd" in exec_cols
            
            user_cols = {row[1] for row in (await conn.execute(text("PRAGMA table_info(users);"))).fetchall()}
            assert "is_admin" in user_cols
            assert "role" in user_cols
            
            live_cols = {row[1] for row in (await conn.execute(text("PRAGMA table_info(live_wallet_links);"))).fetchall()}
            assert "clob_api_secret_enc" in live_cols
            assert "is_live_active" in live_cols
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_migration_failure_rollback_rehearsal(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(migrations, "MIGRATIONS", [
        (1, "valid_step", ["CREATE TABLE test_table (id INTEGER PRIMARY KEY);"], []),
        (2, "faulty_step", ["ALTER TABLE non_existent_table ADD COLUMN foo TEXT;"], []),
    ])
    try:
        async with engine.begin() as conn:
            with pytest.raises(Exception):
                await run_versioned_migrations(conn)
                
            # Verify faulty_step was NOT recorded
            applied = (await conn.execute(text("SELECT version FROM schema_migrations;"))).scalars().all()
            assert 2 not in applied
    finally:
        await engine.dispose()
