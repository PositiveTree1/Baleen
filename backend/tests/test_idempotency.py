"""
Idempotency tests from §13 of the spec.
Tests the dedupe logic that prevents processing the same event twice.
This tests the application-level idempotency mechanism, not the DB constraint
(which is tested implicitly via integration tests).
"""


def dedupe_key(tx_hash: str, log_index: int, user_id: str) -> str:
    """Generate a unique key for deduplication."""
    return f"{tx_hash}:{log_index}:{user_id}"


class IdempotencyChecker:
    """Application-level idempotency checker using an in-memory set."""

    def __init__(self):
        self.seen: set[str] = set()

    def process_event(self, tx_hash: str, log_index: int, user_id: str) -> str:
        key = dedupe_key(tx_hash, log_index, user_id)
        if key in self.seen:
            return "SKIPPED_DUPLICATE"
        self.seen.add(key)
        return "PROCESSED"


def test_first_event_processed():
    checker = IdempotencyChecker()
    result = checker.process_event("0xabc", 4, "u1")
    assert result == "PROCESSED"


def test_duplicate_event_skipped():
    checker = IdempotencyChecker()
    checker.process_event("0xabc", 4, "u1")
    result = checker.process_event("0xabc", 4, "u1")
    assert result == "SKIPPED_DUPLICATE"


def test_same_tx_different_log_index_processed():
    checker = IdempotencyChecker()
    r1 = checker.process_event("0xabc", 4, "u1")
    r2 = checker.process_event("0xabc", 5, "u1")
    assert r1 == "PROCESSED"
    assert r2 == "PROCESSED"


def test_same_tx_same_log_different_user_processed():
    checker = IdempotencyChecker()
    r1 = checker.process_event("0xabc", 4, "u1")
    r2 = checker.process_event("0xabc", 4, "u2")
    assert r1 == "PROCESSED"
    assert r2 == "PROCESSED"

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete
from app.database import SessionLocal, init_db
from app.models import ExecutionLog

@pytest.mark.asyncio
async def test_database_idempotency_unique_constraint():
    await init_db()
    import uuid
    test_user_id = uuid.uuid4()
    async with SessionLocal() as db:
        log1 = ExecutionLog(
            onchain_tx_hash="0xtest_idempotency_tx",
            onchain_log_index=1,
            user_id=test_user_id,
            side="BUY",
            market_condition_id="0xcond_1",
            market_question="Test question",
            whale_entry_price=0.50,
            notional_usd=100.0,
            status="FILLED"
        )
        db.add(log1)
        await db.commit()

        try:
            log2 = ExecutionLog(
                onchain_tx_hash="0xtest_idempotency_tx",
                onchain_log_index=1,
                user_id=test_user_id,
                side="BUY",
                market_condition_id="0xcond_1",
                market_question="Test question",
                whale_entry_price=0.50,
                notional_usd=100.0,
                status="FILLED"
            )
            db.add(log2)
            with pytest.raises(IntegrityError):
                await db.commit()
            await db.rollback()
        finally:
            await db.execute(delete(ExecutionLog).where(ExecutionLog.onchain_tx_hash == "0xtest_idempotency_tx"))
            await db.commit()
