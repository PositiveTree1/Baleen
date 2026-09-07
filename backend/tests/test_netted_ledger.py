import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database import SessionLocal, init_db
from app.models import ExposureLedger
from app.sizing.netted_ledger import (
    update_intended_exposure,
    confirm_exposure_execution,
    check_and_flush_expired_entries,
    close_resolved_ledger_entries
)

@pytest.mark.asyncio
async def test_sub_minimum_accumulation_and_trigger():
    await init_db()
    async with SessionLocal() as db:
        wallet = f"0x{uuid.uuid4().hex[:40]}"
        cid = f"0x{uuid.uuid4().hex}"
        outcome = "Yes"

        # 1. First trade: +$0.60 (Below $1.00 minimum)
        res1 = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome=outcome,
            delta_usd=0.60,
            whale_price=0.55,
            market_question="Test Market A",
            min_threshold_usd=1.00
        )
        assert res1.action == "WAIT"
        assert res1.order_size_usd == 0.0
        assert res1.virtual_position == 0.60
        assert res1.executed_position == 0.0
        assert res1.pending_usd == 0.60

        # 2. Second trade: +$0.55 (Cumulative $1.15 >= $1.00 threshold)
        res2 = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome=outcome,
            delta_usd=0.55,
            whale_price=0.56,
            market_question="Test Market A",
            min_threshold_usd=1.00
        )
        assert res2.action == "EXECUTE"
        assert res2.order_size_usd == 1.15
        assert res2.side == "BUY"
        assert res2.virtual_position == 1.15
        assert res2.executed_position == 0.0
        assert res2.pending_usd == 1.15

        # 3. Confirm execution
        await confirm_exposure_execution(
            db=db,
            ledger_id=res2.ledger_id,
            executed_delta=res2.order_size_usd
        )

        # Verify ledger state in DB
        stmt = select(ExposureLedger).where(ExposureLedger.id == uuid.UUID(res2.ledger_id))
        entry = (await db.execute(stmt)).scalars().first()
        assert entry.virtual_position_usd == 1.15
        assert entry.executed_position_usd == 1.15
        assert entry.status == "executed"

@pytest.mark.asyncio
async def test_same_market_hedge_nets_to_zero():
    await init_db()
    async with SessionLocal() as db:
        wallet = f"0x{uuid.uuid4().hex[:40]}"
        cid = f"0x{uuid.uuid4().hex}"
        outcome = "Yes"

        # 1. Whale buys $0.80
        res1 = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome=outcome,
            delta_usd=0.80,
            whale_price=0.40,
            min_threshold_usd=1.00
        )
        assert res1.action == "WAIT"
        assert res1.pending_usd == 0.80

        # 2. Whale hedges / sells $0.80 back
        res2 = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome=outcome,
            delta_usd=-0.80,
            whale_price=0.42,
            min_threshold_usd=1.00
        )
        # Net virtual position is 0.0 -> zero orders fired!
        assert res2.action == "WAIT"
        assert res2.virtual_position == 0.0
        assert res2.pending_usd == 0.0

@pytest.mark.asyncio
async def test_partial_hedge_crossing_threshold():
    await init_db()
    async with SessionLocal() as db:
        wallet = f"0x{uuid.uuid4().hex[:40]}"
        cid = f"0x{uuid.uuid4().hex}"
        outcome = "No"

        # 1. Initial buy of $2.50
        res1 = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome=outcome,
            delta_usd=2.50,
            whale_price=0.60,
            min_threshold_usd=1.00
        )
        assert res1.action == "EXECUTE"
        assert res1.order_size_usd == 2.50
        assert res1.side == "BUY"

        await confirm_exposure_execution(
            db=db,
            ledger_id=res1.ledger_id,
            executed_delta=2.50
        )

        # 2. Partial hedge sell of -$0.60 (Pending -$0.60 is sub-threshold)
        res2 = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome=outcome,
            delta_usd=-0.60,
            whale_price=0.62,
            min_threshold_usd=1.00
        )
        assert res2.action == "WAIT"
        assert res2.virtual_position == 1.90
        assert res2.executed_position == 2.50
        assert res2.pending_usd == -0.60

        # 3. Second hedge sell of -$0.60 (Pending -$1.20 crosses $1.00 threshold)
        res3 = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome=outcome,
            delta_usd=-0.60,
            whale_price=0.63,
            min_threshold_usd=1.00
        )
        assert res3.action == "EXECUTE"
        assert res3.order_size_usd == 1.20
        assert res3.side == "SELL"

@pytest.mark.asyncio
async def test_expiry_flush_and_drop_behaviors():
    await init_db()
    async with SessionLocal() as db:
        wallet = f"0x{uuid.uuid4().hex[:40]}"
        cid_flush = f"0x{uuid.uuid4().hex}"
        cid_drop = f"0x{uuid.uuid4().hex}"
        outcome = "Yes"

        # Create stale entry for flush
        res_f = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid_flush,
            outcome=outcome,
            delta_usd=0.75,
            whale_price=0.50,
            market_question="Stale Flush Market"
        )
        # Manually backdate last_updated_at to 5 hours ago
        stmt_f = select(ExposureLedger).where(ExposureLedger.id == uuid.UUID(res_f.ledger_id))
        entry_f = (await db.execute(stmt_f)).scalars().first()
        entry_f.last_updated_at = datetime.utcnow() - timedelta(hours=5)
        await db.commit()

        # Flush test
        flushed = await check_and_flush_expired_entries(
            db=db,
            expiry_hours=4.0,
            expiry_behavior="flush",
            min_order_usd=1.00
        )
        matching_flush = [f for f in flushed if f["market_condition_id"] == cid_flush]
        assert len(matching_flush) == 1
        assert matching_flush[0]["size_usd"] == 1.00  # Clamped to min $1.00
        assert matching_flush[0]["side"] == "BUY"

        # Create stale entry for drop
        res_d = await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid_drop,
            outcome=outcome,
            delta_usd=0.75,
            whale_price=0.50,
            market_question="Stale Drop Market"
        )
        stmt_d = select(ExposureLedger).where(ExposureLedger.id == uuid.UUID(res_d.ledger_id))
        entry_d = (await db.execute(stmt_d)).scalars().first()
        entry_d.last_updated_at = datetime.utcnow() - timedelta(hours=5)
        await db.commit()

        # Drop test
        dropped = await check_and_flush_expired_entries(
            db=db,
            expiry_hours=4.0,
            expiry_behavior="drop",
            min_order_usd=1.00
        )
        matching_drop = [d for d in dropped if d["market_condition_id"] == cid_drop]
        assert len(matching_drop) == 0  # Drop doesn't create orders

        await db.refresh(entry_d)
        assert entry_d.status == "expired_unfilled"
        assert entry_d.virtual_position_usd == entry_d.executed_position_usd == 0.0

@pytest.mark.asyncio
async def test_market_resolution_closes_ledger_entries():
    await init_db()
    async with SessionLocal() as db:
        wallet = f"0x{uuid.uuid4().hex[:40]}"
        cid = f"0x{uuid.uuid4().hex}"

        await update_intended_exposure(
            db=db,
            wallet_address=wallet,
            condition_id=cid,
            outcome="Yes",
            delta_usd=0.50,
            whale_price=0.50
        )
        
        closed_count = await close_resolved_ledger_entries(db, cid)
        assert closed_count == 1

        stmt = select(ExposureLedger).where(ExposureLedger.market_condition_id == cid)
        entry = (await db.execute(stmt)).scalars().first()
        assert entry.status == "closed"
