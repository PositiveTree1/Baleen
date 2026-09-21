import json
import time
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models import KeyValue
from app.api.admin import listener_heartbeat
from app.api.signals import listener_checkpoint
from app.services.listener_health import listener_health


@pytest.mark.asyncio
async def test_heartbeat_is_shared_and_cursor_does_not_advance_past_delivery():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    try:
        async with sessions() as db:
            await listener_heartbeat({'block': 500, 'deliveredBlock': 400}, True, db)
        async with sessions() as db:
            assert (await listener_health(db))['status'] == 'ONLINE'
            assert (await listener_checkpoint(db, True))['deliveredBlock'] == 400
            await listener_heartbeat({'block': 501, 'deliveredBlock': 399}, True, db)
            assert (await listener_checkpoint(db, True))['deliveredBlock'] == 400
            row = await db.get(KeyValue, 'listener_heartbeat')
            data = json.loads(row.value)
            data['last_progress_at'] = time.time()-121
            row.value = json.dumps(data)
            await db.commit()
            assert (await listener_health(db))['status'] == 'STALLED'
            data['received_at'] = time.time()-61
            row.value = json.dumps(data)
            await db.commit()
            assert (await listener_health(db))['status'] == 'OFFLINE'
    finally: await engine.dispose()
