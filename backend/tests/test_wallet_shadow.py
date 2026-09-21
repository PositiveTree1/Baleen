from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models import Wallet, WalletEvidence, WalletShadowObservation, KeyValue
from app.services.wallet_shadow import capture_research_batch, capture_window
from app.discovery.wallet_evidence import POLICY_VERSION
from app.services.wallet_reset import GENERATION_KEY


@pytest.mark.asyncio
async def test_shadow_retains_partial_windows_and_rotates_failed_wallets(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    fetch = AsyncMock(side_effect=TimeoutError)
    monkeypatch.setattr("app.services.wallet_shadow.capture_window", fetch)
    try:
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db, db.begin():
            db.add(KeyValue(key=GENERATION_KEY, value="new"))
            for address in ("0xa", "0xb"):
                db.add(Wallet(address=address, status="tracked"))
                db.add(WalletEvidence(wallet_address=address, observed_at=datetime.utcnow()-timedelta(minutes=1),
                    payload={"generation":"new", "policy_version":POLICY_VERSION, "classification":"watchlist"}))
        async with sessions() as db:
            assert await capture_research_batch(db, client=AsyncMock(), limit=1) == 1
            assert await capture_research_batch(db, client=AsyncMock(), limit=1) == 1
            assert {call.args[1] for call in fetch.call_args_list} == {"0xa", "0xb"}
            rows = (await db.execute(select(WalletShadowObservation))).scalars().all()
            assert len(rows) == 2 and all(not r.payload["source_window"]["complete"] for r in rows)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_shadow_does_not_run_before_reset():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    client = AsyncMock()
    try:
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db: assert await capture_research_batch(db, client=client) == 0
        client.fetch_order_book.assert_not_called()
    finally: await engine.dispose()


@pytest.mark.asyncio
async def test_shadow_records_actual_book_times_without_inventing_fills(monkeypatch):
    monkeypatch.setattr("app.services.wallet_shadow.cursor_history", AsyncMock(return_value={"rows":[{"token_id":"123"}],"complete":True}))
    client = AsyncMock()
    client.clob_api_url = "https://example.test"
    client.fetch_order_book.return_value = {"asset_id":"123", "timestamp":"1", "bids":[],"asks":[]}
    client._fetch_with_retry.return_value = {"base_fee":1000}
    result = await capture_window(client, "0xa", 10, 20)
    assert not result["venue_observations"]["123"]["fresh_book"]
    assert result["mode"] == "forward_observation_only" and not result["execution_approved"]
    assert "fill_price" not in result["venue_observations"]["123"]


@pytest.mark.asyncio
async def test_shadow_retains_fee_schedule_and_preserves_books_when_metadata_fails(monkeypatch):
    monkeypatch.setattr("app.services.wallet_shadow.cursor_history", AsyncMock(
        return_value={"rows": [{"token_id": "123"}], "complete": True}))
    client = AsyncMock()
    client.clob_api_url = "https://example.test"
    client.fetch_order_book.return_value = {"asset_id": "123", "market": "0xcondition",
        "timestamp": str(int(datetime.now(timezone.utc).timestamp()*1000)), "bids": [], "asks": []}
    client._fetch_with_retry.return_value = {"base_fee": 1000}
    metadata = {"conditionId": "0xcondition", "feesEnabled": True,
                "feeSchedule": {"rate": .04, "exponent": 1, "takerOnly": True}}
    client.fetch_market_info.return_value = metadata
    result = await capture_window(client, "0xa", 10, 20)
    observed = result["venue_observations"]["123"]
    assert observed["market_metadata"] == metadata
    assert observed["market_metadata_error"] is None
    assert observed["market_observed_at_ms"] >= observed["observed_at_ms"]
    client.fetch_market_info.assert_awaited_once_with("0xcondition")
    client.fetch_market_info.side_effect = TimeoutError
    result = await capture_window(client, "0xa", 10, 20)
    observed = result["venue_observations"]["123"]
    assert observed["market_metadata"] is None
    assert observed["market_metadata_error"] == "TimeoutError"
    assert observed["book"] == client.fetch_order_book.return_value
