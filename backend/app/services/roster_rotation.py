"""Automatic paper-roster rotation after fresh global wallet evaluation."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from app.models import PaperCopyAccount, PaperCopyResearchRun, PaperCopyRosterRotation, SandboxRun
from app.discovery.accounting_snapshot import accounting_snapshot
from app.services.automatic_roster import automatic_active_roster
from app.services.paper_copy_research import append_observation, start_run
from app.sizing.proportional import decimal
from app.database import SessionLocal
from app.discovery.polymarket_client import PolymarketClient


def _cash(report):
    try:
        return decimal(report.get('cash', '0'))
    except (TypeError, ValueError):
        return Decimal('0')


def _pnl(report):
    try:
        value = (report.get('valuation') or {}).get('economic_pnl')
        return None if value is None else decimal(value)
    except (TypeError, ValueError):
        return None


async def rotate_automatic_roster(sessions, user_id, client):
    """Promote fresh top candidates using only free cash from demoted sleeves.

    A retired sleeve remains in the account to process SELL/REDEEM events for
    inventory already copied. It cannot receive further BUY entries.
    """
    async with sessions() as db:
        account = await db.get(PaperCopyAccount, user_id)
        if not account or account.status != 'ACTIVE':
            return None
        runs = (await db.execute(select(PaperCopyResearchRun).where(
            PaperCopyResearchRun.id.in_(account.run_ids), PaperCopyResearchRun.user_id == user_id))).scalars().all()
        if not runs or any(run.policy.get('selection_mode') != 'automatic' for run in runs if run.policy.get('role', 'active') == 'active'):
            return None
        sandbox = await db.get(SandboxRun, account.sandbox_run_id)
        if sandbox is None:
            return None
        desired = await automatic_active_roster(db, sandbox.initial_balance_usd)
        current_addresses = {run.source_wallet for run in runs if run.policy.get('role', 'active') == 'active'}
        promotions = [candidate for candidate in desired if candidate['address'] not in current_addresses]
    snapshots = {}
    for candidate in promotions:
        snapshot = await accounting_snapshot(client, candidate['address'])
        if snapshot.get('status') == 'observed' and snapshot.get('requested_wallet') == candidate['address']:
            snapshots[candidate['address']] = snapshot

    async with sessions() as db:
        account = (await db.execute(select(PaperCopyAccount).where(
            PaperCopyAccount.user_id == user_id).with_for_update())).scalar_one_or_none()
        if not account or account.status != 'ACTIVE':
            return None
        runs = (await db.execute(select(PaperCopyResearchRun).where(
            PaperCopyResearchRun.id.in_(account.run_ids), PaperCopyResearchRun.user_id == user_id))).scalars().all()
        active = [run for run in runs if run.policy.get('role', 'active') == 'active']
        desired_addresses = {candidate['address'] for candidate in desired}
        donors = [run for run in active if run.source_wallet not in desired_addresses]
        promoted, retired, skipped = [], [], []
        for candidate in promotions:
            snapshot = snapshots.get(candidate['address'])
            if not snapshot:
                skipped.append({'wallet': candidate['address'], 'reason': 'Fresh source equity unavailable'})
                continue
            eligible = [(run, _pnl(run.report), _cash(run.report)) for run in donors]
            eligible = [(run, pnl, cash) for run, pnl, cash in eligible if pnl is not None and cash > 0]
            if not eligible:
                skipped.append({'wallet': candidate['address'], 'reason': 'No demoted active sleeve has valued free cash'})
                continue
            donor, donor_pnl, cash = min(eligible, key=lambda item: (item[1], item[0].id))
            donor_id, donor_wallet = donor.id, donor.source_wallet
            transfer = {'id': 'roster-transfer:'+candidate['address']+':'+str(int(datetime.utcnow().timestamp()*1000000)),
                        'timestamp': str(datetime.now(timezone.utc).timestamp()), 'side': 'CAPITAL_OUT',
                        'amount_usd': str(cash), 'reason': 'Free cash moved to newly promoted automatic roster wallet'}
            await append_observation(db, user_id=user_id, run_id=donor_id, source_wallet=donor_wallet,
                                     event=transfer, marks={})
            donor = await db.get(PaperCopyResearchRun, donor_id)
            donor.policy = {**donor.policy, 'role': 'retired', 'retired_at': datetime.utcnow().isoformat(),
                             'retirement_reason': 'Replaced by fresher automatic roster candidate'}
            equity = decimal(snapshot['equity_usd'])
            if equity <= 0 or cash/equity > 1:
                raise ValueError('Automatic roster promotion exceeds fresh source equity')
            new_run = await start_run(db, user_id=user_id, source_wallet=candidate['address'], starting_cash=cash,
                                      ratio=cash/equity, source_cutoff=datetime.now(timezone.utc).timestamp(),
                                      max_slippage_bps=100)
            new_run.policy = {**new_run.policy, 'paper_only': True, 'selection_mode': 'automatic', 'role': 'active',
                              'equity_baseline': snapshot, 'promoted_from_run_id': donor_id}
            account.run_ids = [*account.run_ids, new_run.id]
            donors.remove(donor)
            promoted.append({'wallet': candidate['address'], 'run_id': new_run.id, 'cash': str(cash),
                             'replaced_wallet': donor_wallet, 'replaced_pnl': str(donor_pnl)})
            retired.append({'wallet': donor_wallet, 'run_id': donor_id, 'cash_transferred': str(cash)})
        if promoted or skipped:
            db.add(PaperCopyRosterRotation(user_id=user_id, promoted=promoted, retired=retired, skipped=skipped))
            account.updated_at, account.last_error = datetime.utcnow(), None
            await db.commit()
        return {'promoted': promoted, 'retired': retired, 'skipped': skipped}


async def rotate_all_automatic_rosters(sessions, client):
    async with sessions() as db:
        ids = (await db.execute(select(PaperCopyAccount.user_id).where(
            PaperCopyAccount.status == 'ACTIVE'))).scalars().all()
    return [await rotate_automatic_roster(sessions, user_id, client) for user_id in ids]


async def run_automatic_roster_rotation():
    client = PolymarketClient()
    try:
        return await rotate_all_automatic_rosters(SessionLocal, client)
    finally:
        await client.close()
