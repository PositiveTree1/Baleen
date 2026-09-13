"""Account-owned paper runs. Archival never deletes trade or snapshot evidence."""
from datetime import datetime
from sqlalchemy import select, update, text, event, or_
from sqlalchemy.orm import Session, with_loader_criteria
from app.models import User, SandboxRun, ExecutionLog, PortfolioSnapshot
from app.services.paper_accounting import money


async def financial_lock(db):
    if db.bind.dialect.name == 'postgresql':
        await db.execute(text('SELECT pg_advisory_xact_lock(20260909, 1)'))


async def ensure_user_run(db, user):
    """Adopt pre-run records once, retaining their IDs and financial values."""
    if user.active_paper_run_id:
        run = await db.get(SandboxRun, user.active_paper_run_id)
        if run is None or run.user_id != user.id or run.status != 'ACTIVE':
            raise ValueError('Paper run ownership/state mismatch')
        return run
    run = SandboxRun(user_id=user.id, started_at=user.created_at or datetime.utcnow(),
        initial_balance_usd=user.sandbox_starting_balance_usd,
        high_water_mark_usd=user.sandbox_high_water_mark_usd, status='ACTIVE')
    db.add(run)
    await db.flush()
    await db.execute(update(ExecutionLog).where(ExecutionLog.user_id == user.id,
        ExecutionLog.is_sandbox.is_(True)).values(run_id=run.id))
    await db.execute(update(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user.id).values(run_id=run.id))
    user.active_paper_run_id = run.id
    return run


async def archive_and_start(db, user, starting_balance):
    balance = money(starting_balance)
    if not 100 <= balance <= 10000000:
        raise ValueError('Paper starting balance must be between 100 and 10000000')
    await financial_lock(db)
    # Refresh after acquiring the same lock used by trade effects and MTM.
    await db.refresh(user)
    old = await ensure_user_run(db, user)
    old.status, old.ended_at, old.final_balance_usd = 'ARCHIVED', datetime.utcnow(), user.sandbox_balance_usd
    await db.flush()  # Release the unique active-run slot before inserting its successor.
    now = datetime.utcnow()
    run = SandboxRun(user_id=user.id, started_at=now, source_cutoff_at=now, initial_balance_usd=float(balance),
        high_water_mark_usd=float(balance), status='ACTIVE')
    db.add(run)
    await db.flush()
    user.active_paper_run_id = run.id
    user.sandbox_starting_balance_usd = user.sandbox_balance_usd = user.sandbox_high_water_mark_usd = float(balance)
    db.add(PortfolioSnapshot(user_id=user.id, run_id=run.id, timestamp=run.started_at,
        balance=float(balance), total_pnl=0, active_trades_count=0))
    return run


@event.listens_for(Session, 'do_orm_execute')
def current_run_reads(statement):
    """Operational ORM reads exclude archived personal runs by default.

    Explicit audit/export reads use execution_options(include_archived_runs=True).
    Platform rows and pre-migration accounts remain readable; live data is separate.
    This filter supplements, never replaces, endpoint authentication/ownership.
    """
    if not statement.is_select or statement.execution_options.get('include_archived_runs'):
        return
    active_trade = select(User.active_paper_run_id).where(User.id == ExecutionLog.user_id).correlate(ExecutionLog).scalar_subquery()
    active_snapshot = select(User.active_paper_run_id).where(User.id == PortfolioSnapshot.user_id).correlate(PortfolioSnapshot).scalar_subquery()
    statement.statement = statement.statement.options(
        with_loader_criteria(ExecutionLog, or_(ExecutionLog.is_sandbox.is_(False), ExecutionLog.user_id.is_(None),
            active_trade.is_(None), ExecutionLog.run_id == active_trade), include_aliases=True),
        with_loader_criteria(PortfolioSnapshot, or_(PortfolioSnapshot.user_id.is_(None), active_snapshot.is_(None),
            PortfolioSnapshot.run_id == active_snapshot), include_aliases=True))
