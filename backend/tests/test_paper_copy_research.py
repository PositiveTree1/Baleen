import uuid
from decimal import Decimal
import pytest
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models import User, PaperCopyResearchRun, PaperCopyResearchEvent
from app.services.paper_copy_research import start_run, append_observation, JournalConflict

ADDRESS = "0x" + "1" * 40


def leg(identity, timestamp, side="BUY", quantity=100, **quote):
    return dict(id=identity, timestamp=timestamp, side=side, quantity=quantity, token_id="yes", price=".5",
                observation=dict(timestamp=timestamp+2, token_id="yes", side=side,
                                 fill_price=".5", min_order_size=5, available_quantity=1000,
                                 fee_usd=".01", **quote))


@pytest.fixture
async def journal():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    owner = uuid.uuid4()
    async with sessions() as db, db.begin():
        db.add(User(id=owner, email=f"{owner}@example.test"))
        await db.flush()
        run = await start_run(db, user_id=owner, source_wallet=ADDRESS, starting_cash=100,
                              ratio=".1", source_cutoff=10)
        run_id = run.id
    yield sessions, owner, run_id
    await engine.dispose()


async def append(sessions, owner, run_id, event, **kwargs):
    async with sessions() as db, db.begin():
        return await append_observation(db, user_id=owner, run_id=run_id, source_wallet=ADDRESS,
                                        event=event, marks=kwargs.get("marks", {"yes": ".5"}))


@pytest.mark.asyncio
async def test_restart_retry_partial_exit_and_conflicting_evidence(journal):
    sessions, owner, run_id = journal
    first = await append(sessions, owner, run_id, leg("buy", 10))
    retry = await append(sessions, owner, run_id, leg("buy", 10))
    assert first == retry
    result = await append(sessions, owner, run_id, leg("sell", 12, "SELL", 60))
    assert Decimal(result["valuation"]["cash"]) == Decimal("97.98")
    assert Decimal(result["valuation"]["economic_pnl"]) == Decimal("-.02")
    with pytest.raises(JournalConflict):
        await append(sessions, owner, run_id, leg("buy", 10, quantity=200))
    async with sessions() as db:
        assert (await db.get(PaperCopyResearchRun, run_id)).revision == 2
        assert (await db.execute(select(func.count()).select_from(PaperCopyResearchEvent))).scalar() == 2


@pytest.mark.asyncio
async def test_failed_leg_pauses_entries_but_allows_exit_and_missing_marks(journal):
    sessions, owner, run_id = journal
    await append(sessions, owner, run_id, leg("entry", 10))
    failure = leg("missed", 11)
    del failure["observation"]
    await append(sessions, owner, run_id, failure)
    result = await append(sessions, owner, run_id, leg("paused", 12))
    assert "paused" in result["events"][-1]["reason"]
    result = await append(sessions, owner, run_id, leg("exit", 13, "SELL", 60), marks={})
    assert result["events"][-1]["status"] == "filled"
    assert result["valuation"]["economic_pnl"] is None
    assert result["all_legs_copied"] is False
    assert result["execution_approved"] is False


@pytest.mark.asyncio
async def test_isolation_ordering_and_transaction_rollback(journal):
    sessions, owner, run_id = journal
    with pytest.raises(ValueError, match="not found"):
        await append(sessions, uuid.uuid4(), run_id, leg("other-owner", 10))
    with pytest.raises(ValueError, match="predates"):
        await append(sessions, owner, run_id, leg("old", 9))
    await append(sessions, owner, run_id, leg("first", 11))
    with pytest.raises(ValueError, match="chronologically"):
        await append(sessions, owner, run_id, leg("late", 10))
    async with sessions() as db:
        await append_observation(db, user_id=owner, run_id=run_id, source_wallet=ADDRESS,
                                 event=leg("rollback", 12), marks={"yes": ".5"})
        await db.rollback()
    async with sessions() as db:
        assert (await db.get(PaperCopyResearchRun, run_id)).revision == 1
        assert await db.get(PaperCopyResearchEvent, (run_id, "rollback")) is None


@pytest.mark.asyncio
async def test_missing_journal_history_cannot_silently_change_balances(journal):
    sessions, owner, run_id = journal
    await append(sessions, owner, run_id, leg("first", 10))
    async with sessions() as db, db.begin():
        await db.execute(delete(PaperCopyResearchEvent).where(PaperCopyResearchEvent.run_id == run_id))
    with pytest.raises(JournalConflict, match="Incomplete journal"):
        await append(sessions, owner, run_id, leg("second", 11))


@pytest.mark.asyncio
async def test_exit_of_preexisting_leader_inventory_does_not_block_future_entries(journal):
    sessions, owner, run_id = journal
    result = await append(sessions, owner, run_id, leg('old-inventory-exit', 10, 'SELL'))
    assert result['events'][0]['status'] == 'outside_scope'
    result = await append(sessions, owner, run_id, leg('new-entry', 11))
    assert result['events'][1]['status'] == 'filled'
