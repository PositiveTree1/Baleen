import asyncio
from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.test_real_postgres_batch_a import pg, initialize, URL
from app.models import Wallet, WalletEvidence
from app.services.wallet_reset import reset_wallet_statistics
from app.services.wallet_research import refresh_wallet_evidence

pytestmark = pytest.mark.skipif(not URL, reason="Requires isolated local PostgreSQL")


@pytest.mark.asyncio
async def test_fractional_live_ratio_remains_fixed_with_postgres_precision(pg):
    import uuid
    from decimal import Decimal
    from fastapi import HTTPException
    from app.api.live_setup import save_policy, CopyPolicyRequest
    from app.models import User, LiveExecutionAccount, LiveSourcePosition
    from tests.test_live_copy_coordinator import LIMITS
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    user = User(id=uuid.uuid4(), email='ratio-reset@example.test')
    source = '0x'+'3'*40
    request = CopyPolicyRequest(**LIMITS, source_wallets=[source], copy_ratio=Decimal('.1'))
    async with sessions() as db, db.begin():
        db.add(user)
        await db.flush()
        db.add(LiveExecutionAccount(user_id=user.id, wallet_address='0x'+'2'*40, run_id=uuid.uuid4(), cash=100, reserved_cash=0, enabled=False))
    async with sessions() as db:
        await save_policy(request, user, db)
    async with sessions() as db, db.begin():
        db.add(LiveSourcePosition(user_id=user.id, source_wallet_address=source, token_id='123', quantity=1))
    async with sessions() as db:
        assert (await save_policy(request, user, db))['revision'] == 2
        with pytest.raises(HTTPException) as error:
            await save_policy(request.model_copy(update={'copy_ratio':Decimal('.2')}), user, db)
        assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_inflight_evidence_cannot_resurrect_pre_reset_statistics(pg, monkeypatch):
    await initialize(pg)
    sessions = async_sessionmaker(pg, expire_on_commit=False)
    async with sessions() as db, db.begin():
        db.add(Wallet(address="0xretained", status="active", all_time_pnl_usd=999999))
    fetching, release = asyncio.Event(), asyncio.Event()
    async def collect(*args):
        fetching.set()
        await release.wait()
        return {"classification": "research_candidate", "reasons": [], "metrics": {"economic_pnl": 999999}}
    monkeypatch.setattr("app.services.wallet_research.collect_evidence", collect)
    async def refresh():
        async with sessions() as db: return await refresh_wallet_evidence(db, client=AsyncMock())
    task = asyncio.create_task(refresh())
    try:
        await asyncio.wait_for(fetching.wait(), 5)
        async with sessions() as db, db.begin(): await reset_wallet_statistics(db, "cutover")
        release.set()
        assert await asyncio.wait_for(task, 5) == 0
        async with sessions() as db:
            assert await db.get(WalletEvidence, "0xretained") is None
            assert (await db.get(Wallet, "0xretained")).all_time_pnl_usd is None
    finally:
        release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
