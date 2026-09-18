from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models import Wallet, WalletEvidence, WalletSnapshot, WalletEvidenceArchive, ExecutionLog, KeyValue
from app.services.wallet_reset import reset_wallet_statistics, current_generation, GENERATION_KEY
from app.services.wallet_eligibility import require_research_approval
from app.services.live_risk import RiskRejected


@pytest.mark.asyncio
async def test_reset_archives_statistics_is_idempotent_and_preserves_trades():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db, db.begin():
            db.add(Wallet(address="0xone", all_time_pnl_usd=100000, win_rate_pct=90, status="active", cached_daily_pnl="old"))
            db.add(WalletSnapshot(wallet_address="0xone", pnl_usd=100000))
            db.add(WalletEvidence(wallet_address="0xone", observed_at=datetime.utcnow(), payload={"execution_approved": True}))
            db.add(ExecutionLog(source_wallet_address="0xone", side="BUY", status="FILLED", notional_usd=30))
        async with sessions() as db, db.begin():
            result = await reset_wallet_statistics(db, "reset-one")
            assert result["wallet_count"] == 1 and not result["already_applied"]
        async with sessions() as db, db.begin():
            wallet = await db.get(Wallet, "0xone")
            assert wallet.all_time_pnl_usd is None and wallet.win_rate_pct is None and wallet.cached_daily_pnl is None
            assert wallet.status == "tracked" and await current_generation(db) == "reset-one"
            archive = await db.get(WalletEvidenceArchive, ("reset-one", "0xone"))
            assert archive.payload["wallet"]["all_time_pnl_usd"] == 100000
            assert len(archive.payload["score_snapshots"]) == 1
            assert await db.get(WalletEvidence, "0xone") is None
            assert (await db.execute(select(func.count()).select_from(WalletSnapshot))).scalar() == 0
            trade = (await db.execute(select(ExecutionLog))).scalars().one()
            assert trade.status == "FILLED" and trade.notional_usd == 30
            wallet.all_time_pnl_usd = 123  # New evidence must survive idempotent retry.
            assert (await reset_wallet_statistics(db, "reset-one"))["already_applied"]
            assert wallet.all_time_pnl_usd == 123
            with pytest.raises(RiskRejected, match="Fresh wallet"):
                await require_research_approval(db, "0xone", "BUY")
            await require_research_approval(db, "0xone", "SELL")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reset_rollback_restores_entire_state():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db, db.begin(): db.add(Wallet(address="0xtwo", all_time_pnl_usd=55))
        async with sessions() as db:
            await reset_wallet_statistics(db, "abort")
            await db.rollback()
        async with sessions() as db:
            assert (await db.get(Wallet, "0xtwo")).all_time_pnl_usd == 55
            assert await current_generation(db) == "legacy"
            assert (await db.execute(select(func.count()).select_from(WalletEvidenceArchive))).scalar() == 0
    finally:
        await engine.dispose()
