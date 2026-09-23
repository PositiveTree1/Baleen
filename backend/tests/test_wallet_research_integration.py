from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.database import Base
from app.models import Wallet, WalletEvidence, ExecutionLog
from app.services.wallet_research import refresh_wallet_evidence
from app.scoring.basket import refresh_basket
from app.discovery.wallet_evidence import POLICY_VERSION


@pytest.mark.asyncio
async def test_research_refresh_preserves_positions_and_gates_promotions(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    payload = {"classification": "watchlist", "reasons": ["LOW_OR_INTERMITTENT_ACTIVITY"], "execution_approved": False,
               "metrics": {"fills_per_day_30d": 1}, "trade_coverage": {"complete": True}}
    collect = AsyncMock(return_value=payload)
    monkeypatch.setattr("app.services.wallet_research.collect_evidence", collect)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            w = Wallet(address="0xquiet", status="pending", all_time_pnl_usd=100000, first_seen_at=datetime(2020,1,1))
            db.add(w)
            db.add(ExecutionLog(source_wallet_address=w.address, status="FILLED", side="BUY", is_sandbox=True))
            await db.commit()
            assert await refresh_wallet_evidence(db, client=AsyncMock()) == 1
            assert await db.get(WalletEvidence, w.address) is not None
            assert await refresh_wallet_evidence(db, client=AsyncMock()) == 0
            await refresh_basket(db)
            assert w.status == "tracked"
            trade = (await db.execute(select(ExecutionLog))).scalars().one()
            assert trade.status == "FILLED" and trade.side == "BUY"
            assert collect.await_count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_missing_evidence_cannot_be_promoted_by_legacy_score():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            w = Wallet(address="0xlegacy", status="active", baleen_score=100, all_time_pnl_usd=1000000)
            db.add(w)
            await db.commit()
            await refresh_basket(db)
            assert w.status == "tracked"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_policy_change_reaudits_observed_wallet_without_readding_legacy_registry(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    payload = {"policy_version": POLICY_VERSION, "classification": "watchlist",
               "reasons": ["LOW_OR_INTERMITTENT_ACTIVITY", "QUALITY_SCREEN_PASSED"],
               "execution_approved": False, "metrics": {"fills_per_day_30d": 1},
               "trade_coverage": {"complete": True}}
    collect = AsyncMock(return_value=payload)
    monkeypatch.setattr("app.services.wallet_research.collect_evidence", collect)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            wallet = Wallet(address="0xobserved", status="tracked", first_seen_at=datetime(2020, 1, 1))
            db.add(wallet)
            db.add(WalletEvidence(wallet_address=wallet.address, observed_at=datetime.utcnow(),
                                  payload={**payload, "policy_version": "old-policy"}))
            db.add(Wallet(address="0xlegacy", status="tracked", first_seen_at=datetime(2020, 1, 1)))
            await db.commit()
            assert await refresh_wallet_evidence(db, client=AsyncMock()) == 1
            assert collect.await_args.args[1] == "0xobserved"
            assert await db.get(WalletEvidence, "0xlegacy") is None
    finally:
        await engine.dispose()
