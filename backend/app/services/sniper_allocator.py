"""Paper-only standby-sniper activation using free cash from the weakest sleeve.

Open positions are never sold or resized. A transfer is recorded in the donor
journal before a new sniper run is created, so account cash remains conserved.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from sqlalchemy import select
from app.models import (PaperCopyAccount, PaperCopyResearchRun, PaperCopySniperAllocation,
                        CanonicalSourceEvent, SandboxRun)
from app.discovery.accounting_snapshot import accounting_snapshot
from app.services.automatic_roster import standby_snipers
from app.services.paper_copy_research import append_observation, start_run
from app.sizing.proportional import decimal


MAX_SNIPER_CASH_FRACTION = Decimal('0.25')


def _cash(report):
    try:
        return decimal(report.get('cash', '0'))
    except (TypeError, ValueError):
        return Decimal('0')


def _performance(report):
    value = (report.get('valuation') or {}).get('economic_pnl')
    if value is None:
        return None
    try:
        return decimal(value)
    except (TypeError, ValueError):
        return None


async def _record_rejection(db, *, user_id, source, reason, payload):
    db.add(PaperCopySniperAllocation(user_id=user_id, source_event_id=str(source.id),
                                     source_wallet=source.source_wallet_address, status='NOT_ALLOCATED',
                                     reason=reason, payload=payload))
    await db.commit()


async def process_standby_snipers(sessions, user_id, client, receipts):
    """Create one auditable paper sniper allocation per newly verified BUY fill."""
    async with sessions() as db:
        account = await db.get(PaperCopyAccount, user_id)
        if not account or account.status != 'ACTIVE':
            return
        sandbox = await db.get(SandboxRun, account.sandbox_run_id)
        if sandbox is None or sandbox.source_cutoff_at is None:
            return
        standby = await standby_snipers(db)
        addresses = [row['address'] for row in standby]
        if not addresses:
            return
        sources = (await db.execute(select(CanonicalSourceEvent).where(
            CanonicalSourceEvent.source_wallet_address.in_(addresses),
            CanonicalSourceEvent.side == 'BUY',
            CanonicalSourceEvent.log_index.is_not(None), CanonicalSourceEvent.block_hash.is_not(None),
            CanonicalSourceEvent.emitting_contract.is_not(None),
            CanonicalSourceEvent.block_time >= sandbox.source_cutoff_at,
            CanonicalSourceEvent.status.in_(['CONFIRMED', 'APPLIED'])).order_by(
                CanonicalSourceEvent.block_time, CanonicalSourceEvent.block_number,
                CanonicalSourceEvent.log_index).limit(25))).scalars().all()

    for source in sources:
        async with sessions() as db:
            already = (await db.execute(select(PaperCopySniperAllocation.id).where(
                PaperCopySniperAllocation.user_id == user_id,
                PaperCopySniperAllocation.source_event_id == str(source.id)))).scalar_one_or_none()
        if already:
            continue
        payload = {'source_event_id': str(source.id), 'transaction_hash': source.tx_hash,
                   'source_wallet': source.source_wallet_address, 'source_time': source.block_time.isoformat()}
        try:
            proof = await receipts.source(source)
            snapshot = await accounting_snapshot(client, source.source_wallet_address)
            payload['receipt_verified'] = True
            payload['source_equity_snapshot'] = snapshot
            if snapshot.get('status') != 'observed' or snapshot.get('requested_wallet') != source.source_wallet_address:
                raise ValueError('Fresh source equity is unavailable')
            source_equity = decimal(snapshot['equity_usd'])
            source_notional = decimal(proof['cash_amount'])
            if source_equity <= 0 or source_notional <= 0:
                raise ValueError('Source receipt has no usable equity or cash amount')
        except Exception as exc:
            async with sessions() as db:
                await _record_rejection(db, user_id=user_id, source=source,
                                        reason=f'{type(exc).__name__}: {str(exc)[:180]}', payload=payload)
            continue

        async with sessions() as db:
            account = (await db.execute(select(PaperCopyAccount).where(
                PaperCopyAccount.user_id == user_id).with_for_update())).scalar_one_or_none()
            if not account or account.status != 'ACTIVE':
                return
            exists = (await db.execute(select(PaperCopySniperAllocation.id).where(
                PaperCopySniperAllocation.user_id == user_id,
                PaperCopySniperAllocation.source_event_id == str(source.id)))).scalar_one_or_none()
            if exists:
                continue
            runs = (await db.execute(select(PaperCopyResearchRun).where(
                PaperCopyResearchRun.id.in_(account.run_ids), PaperCopyResearchRun.user_id == user_id))).scalars().all()
            donors = []
            for run in runs:
                if run.policy.get('role', 'active') != 'active':
                    continue
                pnl, cash = _performance(run.report), _cash(run.report)
                if pnl is not None and cash > 0:
                    donors.append((pnl, run.id, run, cash))
            if not donors:
                await _record_rejection(db, user_id=user_id, source=source,
                                        reason='No active sleeve has both fresh valuation and free cash', payload=payload)
                continue
            _, _, donor, donor_cash = min(donors, key=lambda item: (item[0], item[1]))
            commitment = min(source_notional / source_equity, MAX_SNIPER_CASH_FRACTION)
            allocation = min(donor_cash * commitment, source_equity).quantize(Decimal('.00001'), rounding=ROUND_DOWN)
            if allocation <= 0:
                await _record_rejection(db, user_id=user_id, source=source,
                                        reason='Sniper commitment produces no transferable paper cash', payload=payload)
                continue
            donor_id, donor_wallet = donor.id, donor.source_wallet
            transfer_event = {'id': 'sniper-transfer:'+str(source.id),
                              'timestamp': str(source.block_time.replace(tzinfo=timezone.utc).timestamp()),
                              'side': 'CAPITAL_OUT', 'amount_usd': str(allocation),
                              'reason': 'Transferred free cash to verified standby-sniper trade'}
            await append_observation(db, user_id=user_id, run_id=donor_id, source_wallet=donor_wallet,
                                     event=transfer_event, marks={})
            sniper = await start_run(db, user_id=user_id, source_wallet=source.source_wallet_address,
                                     starting_cash=allocation, ratio=allocation/source_equity,
                                     source_cutoff=source.block_time.replace(tzinfo=timezone.utc).timestamp(),
                                     max_slippage_bps=100)
            sniper.policy = {**sniper.policy, 'paper_only': True, 'selection_mode': 'automatic',
                             'role': 'standby_sniper', 'activation_source_event_id': str(source.id),
                             'equity_baseline': snapshot, 'source_commitment_fraction': str(commitment),
                             'donor_run_id': donor_id}
            db.add(PaperCopySniperAllocation(user_id=user_id, source_event_id=str(source.id),
                                              source_wallet=source.source_wallet_address, donor_run_id=donor_id,
                                              sniper_run_id=sniper.id, allocated_cash_usd=str(allocation),
                                              source_commitment_fraction=str(commitment), status='ALLOCATED',
                                              reason='Free cash transferred from the lowest current-P&L active sleeve',
                                              payload=payload))
            account.run_ids = [*account.run_ids, sniper.id]
            account.updated_at, account.last_error = datetime.utcnow(), None
            await db.commit()
