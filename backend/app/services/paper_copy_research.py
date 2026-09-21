"""Durable recorded-observation replay. No signing or order submission.

Callers own the transaction. Optimistic revision checks fence concurrent writers,
including SQLite where SELECT FOR UPDATE provides no serialization. Input must
already be reconciled to source receipt identities; this journal does not assert
receipt authenticity. Replaying retained evidence makes every balance auditable.
"""
import json
import re
from sqlalchemy import select, update
from app.models import PaperCopyResearchRun, PaperCopyResearchEvent
from app.research.proportional_replay import replay
from app.sizing.proportional import decimal


class JournalConflict(ValueError):
    pass


def _json(value):
    # Persist exactly the same numeric representation that replay consumed.
    return json.loads(json.dumps(value, default=str, allow_nan=False))


def _report(policy, events, marks):
    result = replay(events, starting_cash=policy["starting_cash"], ratio=policy["ratio"],
                    marks=marks, delay_seconds=policy["delay_seconds"],
                    max_slippage_bps=policy["max_slippage_bps"], stop_entries_after_missed_leg=True,
                    new_source_fills_only=True)
    result["mode"] = "durable_recorded_observation_replay"
    result["inventory_scope"] = "new_source_fills_only"
    result["receipt_verification"] = "required_upstream"
    result["valuation_basis"] = "caller_supplied_marks_not_independently_verified"
    return result


async def start_run(db, *, user_id, source_wallet, starting_cash, ratio, source_cutoff,
                    delay_seconds=0, max_slippage_bps=100):
    """Explicit research ratio, never inferred from lifetime profit or auto-approved."""
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", source_wallet):
        raise ValueError("Invalid source wallet")
    cash, multiplier, cutoff = map(decimal, (starting_cash, ratio, source_cutoff))
    if cash <= 0 or not 0 < multiplier <= 1 or cutoff < 0:
        raise ValueError("Invalid research allocation")
    policy = {"starting_cash": str(cash), "ratio": str(multiplier), "source_cutoff": str(cutoff),
              "delay_seconds": str(decimal(delay_seconds)),
              "max_slippage_bps": str(decimal(max_slippage_bps))}
    run = PaperCopyResearchRun(user_id=user_id, source_wallet=source_wallet.lower(), policy=policy,
                              revision=0, report=_report(policy, [], {}))
    db.add(run)
    await db.flush()
    return run


async def append_observation(db, *, user_id, run_id, source_wallet, event, marks):
    """Append once and update accounting atomically; caller must rollback on error.

An exact retry preserves its original outcome even when newer books are supplied
elsewhere. A changed payload for the same source identity is a correction conflict,
never a second trade. Missing legs remain recorded and pause subsequent entries.
"""
    run = (await db.execute(select(PaperCopyResearchRun).where(
        PaperCopyResearchRun.id == run_id, PaperCopyResearchRun.user_id == user_id
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if run is None:
        raise ValueError("Research run not found")
    if source_wallet.lower() != run.source_wallet:
        raise ValueError("Source wallet does not match research run")
    event = _json(event)
    identity = event.get("id")
    if not isinstance(identity, str) or not identity:
        raise ValueError("Unique source identity required")
    previous = await db.get(PaperCopyResearchEvent, (run_id, identity))
    if previous is not None:
        if previous.payload != event:
            raise JournalConflict("Conflicting source evidence; correction requires a new research run")
        return run.report
    if decimal(event["timestamp"]) < decimal(run.policy["source_cutoff"]):
        raise ValueError("Source fill predates research baseline")
    rows = (await db.execute(select(PaperCopyResearchEvent).where(
        PaperCopyResearchEvent.run_id == run_id).order_by(PaperCopyResearchEvent.sequence))).scalars().all()
    if [row.sequence for row in rows] != list(range(1, run.revision+1)):
        raise JournalConflict("Incomplete journal history; accounting reconstruction refused")
    marks = _json(marks)
    report = _report(run.policy, [row.payload for row in rows] + [event], marks)
    revision = run.revision
    result = await db.execute(update(PaperCopyResearchRun).where(
        PaperCopyResearchRun.id == run_id, PaperCopyResearchRun.revision == revision
    ).values(revision=revision+1, report=_json(report)).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise JournalConflict("Concurrent paper writer; retry the transaction")
    db.add(PaperCopyResearchEvent(run_id=run_id, source_id=identity, sequence=revision+1,
                                payload=event, valuation_marks=marks))
    await db.flush()
    db.expire(run)
    return report
