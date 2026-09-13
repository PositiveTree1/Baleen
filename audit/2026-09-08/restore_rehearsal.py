"""Local-only PostgreSQL dump/restore rehearsal; creates its own two databases."""
import asyncio
import json
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app import models
from app.migrations import run_versioned_migrations, check_schema_completeness


async def main():
    suffix = uuid.uuid4().hex[:12]
    source, target = f'baleen_src_{suffix}', f'baleen_dst_{suffix}'
    base_url = 'postgresql+asyncpg://postgres@127.0.0.1:55432/'
    admin = create_async_engine(base_url + 'postgres', isolation_level='AUTOCOMMIT')
    async with admin.connect() as conn:
        for name in (source, target):
            await conn.execute(text(f'CREATE DATABASE {name}'))
    uid = uuid.uuid4()
    engine = create_async_engine(base_url + source)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await run_versioned_migrations(conn)
            await conn.execute(text('INSERT INTO users (id, email, sandbox_balance_usd) VALUES (:id, :email, 4321.25)'),
                               {'id': uid, 'email': 'restore-fixture@example.test'})
        await engine.dispose()
        pg_bin = '/usr/lib/postgresql/18/bin/'
        dump = f'/tmp/baleen-restore-{suffix}.dump'
        common = ['-h', '127.0.0.1', '-p', '55432', '-U', 'postgres']
        subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--', pg_bin + 'pg_dump', *common, '-Fc', '-f', dump, source], check=True)
        subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--', pg_bin + 'pg_restore', *common, '--exit-on-error', '-d', target, dump], check=True)
        engine = create_async_engine(base_url + target)
        async with engine.begin() as conn:
            complete, version, detail = await check_schema_completeness(conn)
            assert complete, detail
            row = (await conn.execute(text('SELECT email, sandbox_balance_usd FROM users WHERE id = :id'), {'id': uid})).one()
            assert row == ('restore-fixture@example.test', 4321.25)
            assert await run_versioned_migrations(conn) == version
        print(json.dumps({'passed': True, 'schema_version': version, 'fixture_balance': 4321.25,
                          'source_database': source, 'restored_database': target, 'dump': dump}))
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            for name in (source, target):
                await conn.execute(text(f'DROP DATABASE {name}'))
        await admin.dispose()


if __name__ == '__main__':
    asyncio.run(main())
