"""Receipt-verified forward paper copying with durable per-account decisions."""
import logging
import time
import asyncio
from datetime import datetime, timezone
import httpx
from sqlalchemy import select, exists, cast, String, func
from app.config import settings
from app.database import SessionLocal
from app.models import PaperCopyAccount, PaperCopyResearchRun, PaperCopyResearchEvent, CanonicalSourceEvent, KeyValue, SignalInbox, WalletEvidence
from app.discovery.polymarket_client import PolymarketClient
from app.services.settlement_receipts import PolygonSettlementReader
from app.services.paper_observation import book_quote
from app.services.paper_copy_research import append_observation, _report
from app.sizing.proportional import proportional_quantity, decimal
from app.services.paper_resolution import resolution_evidence
from app.discovery.wallet_evidence import POLICY_VERSION
from app.services.wallet_reset import current_generation
from app.services.sniper_allocator import process_standby_snipers

logger = logging.getLogger(__name__)


async def collect_marks(client, tokens):
    marks = {}
    for token in tokens:
        try:
            book = await client.fetch_order_book(token)
            if (str(book['asset_id']) != token or not 0 <= time.time()*1000-int(book['timestamp']) <= 30000):
                continue
            bids = [decimal(x['price']) for x in book['bids'] if decimal(x['size']) > 0]
            if bids and all(0 < p < 1 for p in bids): marks[token] = str(max(bids))
        except (KeyError, TypeError, ValueError):
            continue
    return marks


async def process_run(sessions, run_id, client, receipts):
    async with sessions() as db:
        run = await db.get(PaperCopyResearchRun, run_id)
        if run is None: return
        uid, policy, address = run.user_id, run.policy, run.source_wallet
        consumed = exists(select(PaperCopyResearchEvent.source_id).where(
            PaperCopyResearchEvent.run_id == run_id,
            func.replace(PaperCopyResearchEvent.source_id, '-', '') == func.replace(cast(CanonicalSourceEvent.id, String), '-', '')))
        sources = (await db.execute(select(CanonicalSourceEvent).where(
            CanonicalSourceEvent.source_wallet_address == address,
            CanonicalSourceEvent.log_index.is_not(None), CanonicalSourceEvent.block_hash.is_not(None),
            CanonicalSourceEvent.emitting_contract.is_not(None),
            CanonicalSourceEvent.block_time >= datetime.fromtimestamp(float(policy['source_cutoff']), timezone.utc).replace(tzinfo=None),
            CanonicalSourceEvent.status.in_(['CONFIRMED', 'APPLIED']), ~consumed).order_by(
                CanonicalSourceEvent.block_time, CanonicalSourceEvent.block_number, CanonicalSourceEvent.log_index).limit(25))).scalars().all()
    for source in sources:
        # Pending or invalid receipts must never be presented as simulated fills.
        proof = await receipts.source(source)
        event = {'id': str(source.id), 'timestamp': str(source.block_time.replace(tzinfo=timezone.utc).timestamp()),
                 'side': source.side, 'quantity': str(proof['quantity']), 'price': str(proof['price']),
                 'token_id': source.token_id, 'condition_id': source.condition_id, 'receipt': {'transaction_hash': source.tx_hash,
                    'log_index': source.log_index, 'block_hash': source.block_hash, 'verified': True}}
        try:
            if source.side == 'BUY' and policy.get('role') == 'retired':
                raise ValueError('Wallet retired from active roster; new entries are disabled while exits remain monitored')
            quantity = proportional_quantity(proof['quantity'], policy['ratio'])
            market = await client.fetch_market_info(source.condition_id)
            book = await client.fetch_order_book(source.token_id)
            event['observation'] = book_quote(book, market, token=source.token_id, condition=source.condition_id,
                                             side=source.side, quantity=quantity, now_ms=int(time.time()*1000))
        except (ValueError, KeyError, TypeError) as exc:
            event['observation_error'] = str(exc)
        async with sessions() as db:
            account = (await db.execute(select(PaperCopyAccount).where(PaperCopyAccount.user_id == uid).with_for_update())).scalar_one_or_none()
            if not account or account.status != 'ACTIVE' or run_id not in account.run_ids:
                return
            existing = await db.get(PaperCopyResearchEvent, (run_id, str(source.id)))
            if existing: continue  # Another replica already stored its original observation.
            evidence = await db.get(WalletEvidence, address)
            if (source.side == 'BUY' and evidence and evidence.payload.get('policy_version') == POLICY_VERSION
                    and evidence.payload.get('generation') == await current_generation(db)
                    and (datetime.utcnow()-evidence.observed_at).total_seconds() < 86400
                    and evidence.payload.get('classification') == 'excluded'):
                event['observation_error'] = 'Wallet re-evaluation excluded new entries: '+', '.join(evidence.payload.get('reasons', []))
            latest = await db.get(PaperCopyResearchRun, run_id)
            marks = await collect_marks(client, set(latest.report.get('positions', {})) | {source.token_id})
            report = await append_observation(db, user_id=uid, run_id=run_id, source_wallet=address, event=event, marks=marks)
            latest = await db.get(PaperCopyResearchRun, run_id)
            report.update(receipt_verification='canonical_polygon_receipts', valuation_basis='observed_best_bids',
                          valuation_observed_at=datetime.utcnow().isoformat(), mode='forward_paper_copy')
            latest.report = report
            account.updated_at, account.last_error = datetime.utcnow(), None
            await db.commit()
    # Mark inventory even when the leader is quiet. Missing markets leave P&L
    # unavailable; old entry prices are never substituted.
    async with sessions() as db:
        account = (await db.execute(select(PaperCopyAccount).where(PaperCopyAccount.user_id == uid).with_for_update())).scalar_one_or_none()
        if not account or account.status != 'ACTIVE' or run_id not in account.run_ids: return
        run = await db.get(PaperCopyResearchRun, run_id)
        rows = (await db.execute(select(PaperCopyResearchEvent).where(
            PaperCopyResearchEvent.run_id == run_id).order_by(PaperCopyResearchEvent.sequence))).scalars().all()
        if [r.sequence for r in rows] != list(range(1, run.revision+1)):
            raise ValueError('Incomplete paper journal')
        # Settle only after all watched source logs through the payout observation
        # were durably delivered and processed. No settlement races queued exits.
        import json
        heartbeat = await db.get(KeyValue, 'listener_heartbeat')
        progress = json.loads(heartbeat.value) if heartbeat else {}
        inbox_pending = (await db.execute(select(func.count()).select_from(SignalInbox).where(
            SignalInbox.payload['walletAddress'].as_string() == address,
            SignalInbox.status.in_(['PENDING', 'FAILED'])))).scalar()
        if len(sources) < 25 and not inbox_pending and time.time()-progress.get('received_at', 0) < 60:
            conditions = {r.payload['token_id']: r.payload.get('condition_id') for r in rows if r.payload.get('condition_id')}
            for token, quantity in dict(run.report.get('positions', {})).items():
                condition = conditions.get(token)
                if not condition: continue
                market = await client.fetch_market_info(condition)
                resolution = await resolution_evidence(receipts, condition, token, market,
                    delivered_height=progress.get('deliveredBlock', 0)-1)
                if not resolution or progress.get('deliveredBlock', 0) <= resolution['block_number']: continue
                event = {'id': 'resolution:'+condition+':'+token, 'side': 'REDEEM', 'token_id': token,
                         'condition_id': condition, 'quantity': quantity, 'timestamp': str(time.time()),
                         'resolution': resolution}
                await append_observation(db, user_id=uid, run_id=run_id, source_wallet=address, event=event, marks={})
                run = await db.get(PaperCopyResearchRun, run_id)
            rows = (await db.execute(select(PaperCopyResearchEvent).where(
                PaperCopyResearchEvent.run_id == run_id).order_by(PaperCopyResearchEvent.sequence))).scalars().all()
        marks = await collect_marks(client, run.report.get('positions', {}))
        report = _report(run.policy, [r.payload for r in rows], marks)
        report.update(receipt_verification='canonical_polygon_receipts', valuation_basis='observed_best_bids',
                      valuation_observed_at=datetime.utcnow().isoformat(), mode='forward_paper_copy', valuation_marks=marks)
        run.report = report
        account.updated_at, account.last_error = datetime.utcnow(), None
        await db.commit()


async def run_paper_copy():
    async with SessionLocal() as db:
        accounts = (await db.execute(select(PaperCopyAccount).where(PaperCopyAccount.status == 'ACTIVE'))).scalars().all()
    if not accounts: return
    client = PolymarketClient()
    try:
        async with httpx.AsyncClient(base_url=settings.POLYGON_SETTLEMENT_RPC_URL or 'https://polygon-bor-rpc.publicnode.com',
                                     timeout=10, follow_redirects=False) as rpc:
            receipts = PolygonSettlementReader(rpc)
            for account in accounts:
                for run_id in account.run_ids:
                    try:
                        await asyncio.wait_for(process_run(SessionLocal, run_id, client, receipts), 45)
                    except Exception as exc:
                        logger.warning('Paper copy delayed: %s', type(exc).__name__)
                        async with SessionLocal() as db:
                            current = (await db.execute(select(PaperCopyAccount).where(PaperCopyAccount.user_id == account.user_id).with_for_update())).scalar_one_or_none()
                            if current and run_id in current.run_ids:
                                current.last_error = f'{type(exc).__name__}: {str(exc)[:240]}'
                                failed_run = await db.get(PaperCopyResearchRun, run_id)
                                if failed_run:
                                    failed_run.report = {**failed_run.report, 'worker_error': current.last_error}
                                await db.commit()
                try:
                    await asyncio.wait_for(process_standby_snipers(SessionLocal, account.user_id, client, receipts), 45)
                except Exception as exc:
                    logger.warning('Standby sniper allocation delayed: %s', type(exc).__name__)
    finally:
        await client.close()
