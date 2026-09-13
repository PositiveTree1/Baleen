import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
from sqlalchemy import select, func, delete
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine, SessionLocal, init_db
from app.models import User, Wallet, ExecutionLog, SignalInbox, CanonicalSourceEvent, ExposureLedger
from app.services.live_poller import LiveTradeMirrorService
from app.sizing.netted_ledger import get_or_create_ledger_entry, update_intended_exposure
from app.main import app
from app.config import settings


@pytest.fixture(autouse=True)
async def clean_batch_b_state():
    await init_db()
    async with SessionLocal() as db:
        await db.execute(delete(ExposureLedger).where(ExposureLedger.wallet_address.like("0xbb%")))
        await db.execute(delete(ExecutionLog).where(ExecutionLog.source_wallet_address.like("0xbb%")))
        await db.execute(delete(CanonicalSourceEvent).where(CanonicalSourceEvent.source_wallet_address.like("0xbb%")))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xbb%")))
        await db.execute(delete(User).where(User.email.like("%@batch_b.invalid")))
        await db.commit()
    yield
    async with SessionLocal() as db:
        await db.execute(delete(ExposureLedger).where(ExposureLedger.wallet_address.like("0xbb%")))
        await db.execute(delete(ExecutionLog).where(ExecutionLog.source_wallet_address.like("0xbb%")))
        await db.execute(delete(CanonicalSourceEvent).where(CanonicalSourceEvent.source_wallet_address.like("0xbb%")))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xbb%")))
        await db.execute(delete(User).where(User.email.like("%@batch_b.invalid")))
        await db.commit()


@pytest.mark.asyncio
async def test_dual_provider_single_economic_event():
    """
    R5 Invariant: The same underlying economic event received via both
    indexed chain listener (log_index=7) and unindexed REST poller (log_index=None)
    must produce exactly 1 intended ExecutionLog.
    """
    addr = "0xbb" + "c" * 38
    cid = "0x" + "d" * 64
    duplicate_tx = "0x" + "e" * 64
    now = datetime.utcnow()
    uid = uuid.uuid4()

    async with SessionLocal() as db:
        db.add(Wallet(
            address=addr,
            status="active",
            tier="gold_sniper",
            dormant=False,
            is_hft=False,
            avg_trades_per_day=2,
            baleen_score=75,
            all_time_pnl_usd=50000,
            win_rate_pct=90,
            wilson_lb=85
        ))
        db.add(User(
            id=uid,
            email=f"dual_provider_{uuid.uuid4().hex[:8]}@batch_b.invalid",
            sandbox_starting_balance_usd=10000,
            sandbox_balance_usd=10000,
            sandbox_high_water_mark_usd=10000
        ))
        await db.commit()

    service = LiveTradeMirrorService()
    with patch("app.services.event_logger.log_event", new=AsyncMock()):
        # First arrival: indexed chain log
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id=cid,
            title="Dual Ingestion Market",
            side="BUY",
            price=0.5,
            cash_usd=1000,
            dt=now,
            asset="111",
            event_slug="dual",
            icon="dual",
            tx_hash=duplicate_tx,
            log_index=7
        )
        # Second arrival: unindexed REST observation
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id=cid,
            title="Dual Ingestion Market",
            side="BUY",
            price=0.5,
            cash_usd=1000,
            dt=now,
            asset="111",
            event_slug="dual",
            icon="dual",
            tx_hash=duplicate_tx,
            log_index=None
        )

    async with SessionLocal() as db:
        logs = (await db.execute(
            select(ExecutionLog).where(
                ExecutionLog.user_id == uid,
                ExecutionLog.onchain_tx_hash == duplicate_tx
            )
        )).scalars().all()
        assert len(logs) == 1, f"Expected 1 execution log for duplicate provider event, found {len(logs)}"
        assert logs[0].onchain_log_index == 7


@pytest.mark.asyncio
async def test_signal_inbox_atomic_persistence_and_conflict_detection():
    """
    R4 Invariant: /api/signals persists to signal_inbox, accepts identical replays idempotently,
    and returns 409 Conflict if payload attributes disagree for the same identity.
    """
    tx_hash = "0x" + "f" * 64
    addr = "0xbb" + "a" * 38
    signal_payload = {
        "walletAddress": addr,
        "side": "BUY",
        "assetId": "999888777",
        "amountFilled": "100000000", "amountUnit": "raw_6",
        "price": "0.55",
        "transactionHash": tx_hash,
        "logIndex": 2,
        "blockNumber": 65000000,
        "timestamp": 1787144000000
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First submission -> 200 Queued
        res1 = await client.post("/api/signals", json=signal_payload)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "queued"
        assert data1["accepted"] is True
        inbox_id = data1["inboxId"]

        # Identical replay -> 200 Duplicate Accepted (safe idempotent ACK)
        res2 = await client.post("/api/signals", json=signal_payload)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "queued"
        assert data2["duplicate"] is True
        assert data2["inboxId"] == inbox_id

        # Conflicting payload with same idempotency key (different side) -> 409 Conflict
        conflicting_payload = dict(signal_payload)
        conflicting_payload["side"] = "SELL"
        res3 = await client.post("/api/signals", json=conflicting_payload)
        assert res3.status_code == 409

    async with SessionLocal() as db:
        inbox_rows = (await db.execute(
            select(SignalInbox).where(SignalInbox.idempotency_key == f"137:{tx_hash}:{2}:{addr}")
        )).scalars().all()
        assert len(inbox_rows) == 1


@pytest.mark.asyncio
async def test_unresolved_condition_id_quarantined():
    """
    R5 Invariant: Signals with unresolved condition IDs enter quarantine state
    and MUST NOT produce executable orders.
    """
    addr = "0xbb" + "7" * 38
    now = datetime.utcnow()
    uid = uuid.uuid4()

    async with SessionLocal() as db:
        db.add(Wallet(address=addr, status="active", tier="gold_sniper", baleen_score=70))
        db.add(User(id=uid, email=f"quarantine_{uuid.uuid4().hex[:8]}@batch_b.invalid", sandbox_balance_usd=10000))
        await db.commit()

    service = LiveTradeMirrorService()
    # Mock resolution failure: market metadata returns None
    service._resolve_market_metadata = AsyncMock(return_value={"condition_id": None, "title": "Unresolvable Question", "event_slug": "", "icon": ""})

    with patch("app.services.event_logger.log_event", new=AsyncMock()):
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id=None,  # Unknown condition ID
            title="Unknown Market",
            side="BUY",
            price=0.5,
            cash_usd=1000,
            dt=now,
            asset="unresolved_asset",
            tx_hash="0x" + "8" * 64,
            log_index=0
        )

    async with SessionLocal() as db:
        # Verify NO execution log was created for user
        logs = (await db.execute(
            select(ExecutionLog).where(ExecutionLog.user_id == uid)
        )).scalars().all()
        assert len(logs) == 0

        # Verify CanonicalSourceEvent was quarantined
        canon = (await db.execute(
            select(CanonicalSourceEvent).where(CanonicalSourceEvent.source_wallet_address == addr)
        )).scalars().first()
        assert canon is not None
        assert canon.status == "QUARANTINED"


@pytest.mark.asyncio
async def test_multi_fills_single_tx_distinct():
    """
    R5 Invariant: Multiple distinct fills within the same transaction (e.g. logIndex=0 and logIndex=1)
    must remain distinct and not deduplicated by tx_hash alone.
    """
    addr = "0xbb" + "9" * 38
    cid = "0x" + "9" * 64
    tx_hash = "0x" + "1" * 64
    now = datetime.utcnow()
    uid = uuid.uuid4()

    async with SessionLocal() as db:
        db.add(Wallet(address=addr, status="active", tier="gold_sniper", baleen_score=70))
        db.add(User(id=uid, email=f"multifill_{uuid.uuid4().hex[:8]}@batch_b.invalid", sandbox_balance_usd=10000))
        await db.commit()

    service = LiveTradeMirrorService()
    with patch("app.services.event_logger.log_event", new=AsyncMock()):
        # Fill 0
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id=cid,
            title="Multi Fill Market",
            side="BUY",
            price=0.5,
            cash_usd=500,
            dt=now,
            asset="111",
            tx_hash=tx_hash,
            log_index=0
        )
        # Fill 1
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id=cid,
            title="Multi Fill Market",
            side="BUY",
            price=0.6,
            cash_usd=600,
            dt=now,
            asset="111",
            tx_hash=tx_hash,
            log_index=1
        )

    async with SessionLocal() as db:
        logs = (await db.execute(
            select(ExecutionLog).where(
                ExecutionLog.user_id == uid,
                ExecutionLog.onchain_tx_hash == tx_hash
            )
        )).scalars().all()
        assert len(logs) == 2, f"Expected 2 fills for multi-log tx, found {len(logs)}"
        indices = {l.onchain_log_index for l in logs}
        assert indices == {0, 1}


@pytest.mark.asyncio
async def test_account_and_mode_isolated_exposure():
    """
    R5 Invariant: ExposureLedger correctly scopes intended exposure by
    (user_id, mode, run_id).
    """
    u1 = uuid.uuid4()
    u2 = uuid.uuid4()
    r1 = uuid.uuid4()
    cid = "0xcond_isolate"
    addr = "0xbb" + "e" * 38

    async with SessionLocal() as db:
        # Create ledger for u1 sandbox
        e1 = await get_or_create_ledger_entry(db, addr, cid, "Yes", user_id=u1, mode="sandbox", run_id=None)
        # Create ledger for u2 sandbox
        e2 = await get_or_create_ledger_entry(db, addr, cid, "Yes", user_id=u2, mode="sandbox", run_id=None)
        # Create ledger for u1 run1
        e3 = await get_or_create_ledger_entry(db, addr, cid, "Yes", user_id=u1, mode="benchmark", run_id=r1)
        await db.commit()

        assert e1.id != e2.id
        assert e1.id != e3.id
        assert e1.user_id == u1
        assert e2.user_id == u2
        assert e3.mode == "benchmark"
        assert e3.run_id == r1
