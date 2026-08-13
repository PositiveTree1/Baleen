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
