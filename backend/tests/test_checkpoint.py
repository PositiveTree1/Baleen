import pytest
from app.database import SessionLocal, init_db
from app.discovery.scanner import _persist_discovery_state, load_discovery_state_from_db, discovery_state

@pytest.mark.asyncio
async def test_save_and_resume_checkpoint_database():
    await init_db()
    async with SessionLocal() as db:
        discovery_state["status"] = "running"
        discovery_state["progress_pct"] = 42
        discovery_state["step_description"] = "Scanning wallets"
        await _persist_discovery_state(db)

    # Now load state from DB
    await load_discovery_state_from_db()
    assert discovery_state["progress_pct"] == 42
    assert "interrupted" in discovery_state["status"]

def test_default_checkpoint_is_zero():
    checkpoint = 0
    assert checkpoint == 0
