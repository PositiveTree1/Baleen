"""Authenticated server-owned paper following; no live funds or execution grants."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from app.auth import get_current_user
from app.database import get_db
from app.models import User, Wallet, PaperCopyAccount, PaperCopyResearchRun, PaperCopySniperAllocation, PaperCopyRosterRotation, WalletEvidence
from app.services.paper_copy_research import start_run
from app.services.paper_runs import archive_and_start
from app.discovery.accounting_snapshot import accounting_snapshot
from app.discovery.polymarket_client import PolymarketClient
from app.sizing.proportional import decimal
from app.services.automatic_roster import automatic_active_roster, standby_snipers

router = APIRouter(prefix='/api/paper-copy', tags=['paper-copy'])


@router.get('/wallets')
async def selectable_wallets(search: str = Query(default='', max_length=100),
                             user: User = Depends(get_current_user), db=Depends(get_db)):
    from sqlalchemy import or_
    query = select(Wallet).order_by(Wallet.name.asc().nullslast(), Wallet.address).limit(250)
    if search:
        query = query.where(or_(Wallet.address.ilike('%'+search+'%'), Wallet.name.ilike('%'+search+'%'),
                               Wallet.pseudonym.ilike('%'+search+'%')))
    rows = (await db.execute(query)).scalars().all()
    account = await db.get(PaperCopyAccount, user.id)
    if account:
        sources = (await db.execute(select(PaperCopyResearchRun.source_wallet).where(
            PaperCopyResearchRun.id.in_(account.run_ids), PaperCopyResearchRun.user_id == user.id))).scalars().all()
        selected = (await db.execute(select(Wallet).where(Wallet.address.in_(sources)))).scalars().all()
        rows = list({w.address: w for w in [*selected, *rows]}.values())
    return [{'address': w.address, 'name': w.name, 'pseudonym': w.pseudonym} for w in rows]


class StartPaperCopy(BaseModel):
    wallets: list[str] = Field(min_length=1, max_length=10)
    starting_cash: Decimal = Field(ge=20, le=10000000)

    @field_validator('wallets')
    @classmethod
    def addresses(cls, values):
        import re
        result = [v.lower() for v in values]
        if len(set(result)) != len(result) or any(not re.fullmatch(r'0x[0-9a-f]{40}', v) for v in result):
            raise ValueError('Distinct wallet addresses required')
        return result


class StartAutomaticPaperCopy(BaseModel):
    starting_cash: Decimal = Field(ge=20, le=10000000)


@router.get('')
async def get_paper_copy(user: User = Depends(get_current_user), db=Depends(get_db)):
    snipers = await standby_snipers(db)
    account = await db.get(PaperCopyAccount, user.id)
    if account is None:
        return {'status': 'NOT_CONFIGURED', 'runs': [], 'standby_snipers': snipers,
                'execution_approved': False, 'mode': 'paper_only'}
    rows = (await db.execute(select(PaperCopyResearchRun).where(
        PaperCopyResearchRun.id.in_(account.run_ids), PaperCopyResearchRun.user_id == user.id))).scalars().all()
    order = {run_id: index for index, run_id in enumerate(account.run_ids)}
    rows.sort(key=lambda row: order.get(row.id, len(order)))
    runs = []
    for r in rows:
        wallet = await db.get(Wallet, r.source_wallet)
        report = r.report
        try:
            stamp = datetime.fromisoformat(report.get('valuation_observed_at', r.created_at.isoformat()))
            stale_run = (datetime.utcnow()-stamp).total_seconds() > 60
        except (ValueError, TypeError): stale_run = True
        if stale_run or report.get('worker_error'):
            report = {**report, 'valuation': {'economic_pnl': None,
                'reason': report.get('worker_error') or 'Current marks unavailable'}}
        runs.append({'id': r.id, 'wallet': r.source_wallet, 'name': (wallet.name or wallet.pseudonym) if wallet else None,
                     'policy': r.policy, 'report': report, 'revision': r.revision})
    from app.services.listener_health import listener_health
    listener_data = await listener_health(db)
    # Old reports are retained for audit, but never displayed as current equity.
    stale = (datetime.utcnow()-account.updated_at).total_seconds() > 60
    if stale or account.last_error:
        for row in runs:
            row['report'] = {**row['report'], 'valuation': {'economic_pnl': None,
                'reason': 'Worker delayed; current valuation unavailable'}}
    selection_mode = runs[0]['policy'].get('selection_mode', 'manual') if runs else 'automatic'
    allocations = (await db.execute(select(PaperCopySniperAllocation).where(
        PaperCopySniperAllocation.user_id == user.id).order_by(PaperCopySniperAllocation.created_at.desc()).limit(20))).scalars().all()
    return {'status': account.status, 'runs': runs, 'standby_snipers': snipers,
            'selection_mode': selection_mode, 'last_error': account.last_error,
            'sniper_allocations': [{'source_event_id': row.source_event_id, 'source_wallet': row.source_wallet,
                                    'donor_run_id': row.donor_run_id, 'sniper_run_id': row.sniper_run_id,
                                    'allocated_cash_usd': row.allocated_cash_usd, 'status': row.status,
                                    'reason': row.reason, 'created_at': row.created_at.isoformat()} for row in allocations],
            'roster_rotations': [{'promoted': row.promoted, 'retired': row.retired, 'skipped': row.skipped,
                                  'created_at': row.created_at.isoformat()} for row in (await db.execute(
                                      select(PaperCopyRosterRotation).where(PaperCopyRosterRotation.user_id == user.id).order_by(
                                          PaperCopyRosterRotation.created_at.desc()).limit(10))).scalars().all()],
            'updated_at': account.updated_at, 'listener': listener_data['status'],
            'listener_progress': listener_data,
            'execution_approved': False, 'mode': 'paper_only'}


async def _start_paper_copy(wallets, starting_cash, user, db, *, selection_mode):
    from app.config import settings
    if not settings.RUN_BACKGROUND_WORKERS:
        raise HTTPException(503, 'Paper-copy worker is disabled on this deployment')
    known = set((await db.execute(select(Wallet.address).where(Wallet.address.in_(wallets)))).scalars())
    if known != set(wallets): raise HTTPException(422, 'Selected wallets are not admitted to the registry')
    from app.discovery.wallet_evidence import POLICY_VERSION
    from app.services.wallet_reset import current_generation
    generation = await current_generation(db)
    for address in wallets:
        evidence = await db.get(WalletEvidence, address)
        if (evidence and evidence.payload.get('policy_version') == POLICY_VERSION
                and evidence.payload.get('generation') == generation
                and (datetime.utcnow()-evidence.observed_at).total_seconds() < 86400
                and evidence.payload.get('classification') == 'excluded'):
            raise HTTPException(409, f'{address} fails current wallet screening: '+', '.join(evidence.payload.get('reasons', [])))
    # Fetch fresh baselines before taking financial locks. A failed fetch cannot
    # archive the existing run or start a partially funded account.
    client = PolymarketClient()
    try:
        snapshots = await asyncio.wait_for(asyncio.gather(*(accounting_snapshot(client, a) for a in wallets)), 45)
    except TimeoutError:
        raise HTTPException(503, 'Current wallet equity unavailable; existing run preserved')
    finally:
        await client.close()
    budget = starting_cash/len(wallets)
    ratios = []
    for address, snapshot in zip(wallets, snapshots):
        if snapshot.get('status') != 'observed' or snapshot.get('requested_wallet') != address:
            raise HTTPException(503, f'Current equity unavailable for {address}; existing run preserved')
        equity = decimal(snapshot['equity_usd'])
        if equity <= 0 or budget/equity > 1:
            raise HTTPException(422, f'Allocation exceeds observed source equity for {address}')
        ratios.append(budget/equity)
    sandbox = await archive_and_start(db, user, starting_cash, minimum_balance=20)
    cutoff = datetime.now(timezone.utc).timestamp()
    ids = []
    for address, snapshot, ratio in zip(wallets, snapshots, ratios):
        run = await start_run(db, user_id=user.id, source_wallet=address, starting_cash=budget,
                              ratio=ratio, source_cutoff=cutoff, max_slippage_bps=100)
        run.policy = {**run.policy, 'equity_baseline': snapshot, 'paper_only': True,
                      'selection_mode': selection_mode, 'role': 'active'}
        ids.append(run.id)
    account = await db.get(PaperCopyAccount, user.id)
    if account is None:
        account = PaperCopyAccount(user_id=user.id)
        db.add(account)
    account.sandbox_run_id, account.run_ids, account.status = sandbox.id, ids, 'ACTIVE'
    account.updated_at, account.last_error = datetime.utcnow(), None
    await db.commit()
    return await get_paper_copy(user, db)


@router.post('/start')
async def start_paper_copy(req: StartPaperCopy, user: User = Depends(get_current_user), db=Depends(get_db)):
    """Retained for API compatibility; the dashboard uses automatic selection."""
    return await _start_paper_copy(req.wallets, req.starting_cash, user, db, selection_mode='manual')


@router.post('/start-automatic')
async def start_automatic_paper_copy(req: StartAutomaticPaperCopy, user: User = Depends(get_current_user), db=Depends(get_db)):
    from app.config import settings
    if not settings.RUN_BACKGROUND_WORKERS:
        raise HTTPException(503, 'Paper-copy worker is disabled on this deployment')
    roster = await automatic_active_roster(db, req.starting_cash)
    if not roster:
        raise HTTPException(503, 'No fresh eligible active wallets yet; discovery is still evaluating the registry')
    return await _start_paper_copy([row['address'] for row in roster], req.starting_cash, user, db,
                                   selection_mode='automatic')
