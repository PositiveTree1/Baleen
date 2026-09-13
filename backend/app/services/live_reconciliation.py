"""Authenticated reconciliation; no submission, invented fee, or balance adjustment.

Fee-bearing fills require settlement fee evidence before accounting. Incomplete
exchange reads halt new risk and preserve reservations rather than guessing.
"""
import asyncio
from datetime import datetime
from decimal import Decimal
import uuid
from sqlalchemy import select, text
from app.models import LiveExecutionAccount, LiveOrderIntent, LivePosition, LiveReconciliation, LiveWalletBaseline
from app.services.clob_gateway import ExchangeUnavailable
from app.services.live_order_journal import LiveOrderJournal, number
from app.services.settlement_receipts import SettlementPending


class ReconciliationMismatch(ValueError):
    pass


def confirmed_fill(trade, order, wallet, *, require_zero_fee=True):
    """Normalize only the participant matching our signed order, never the whole tx."""
    if trade.get('status') not in ('CONFIRMED', 'TRADE_STATUS_CONFIRMED'):
        if str(trade.get('status', '')).removeprefix('TRADE_STATUS_') in ('MATCHED','MINED','RETRYING'):
            raise SettlementPending('Associated trade is awaiting confirmation')
        raise ReconciliationMismatch('Associated trade is not confirmed')
    if trade.get('taker_order_id', '').lower() == order.signed_order_hash.lower():
        participant = trade
        qty = number(trade.get('size', -1), positive=True)
    else:
        matches = [m for m in trade.get('maker_orders', [])
                   if m.get('order_id', '').lower() == order.signed_order_hash.lower()]
        if len(matches) != 1:
            raise ReconciliationMismatch('Trade participant identity mismatch')
        participant = matches[0]
        qty = number(participant.get('matched_amount', -1), positive=True)
    if (participant.get('asset_id') != order.token_id or participant.get('side') != order.side
            or participant.get('maker_address', '').lower() != wallet.lower()):
        raise ReconciliationMismatch('Trade token, side or wallet mismatch')
    # Missing rates are unknown. A nonzero rate is not proof of the actual fee
    # paid (rounding, fee asset, per-match allocation); never manufacture it.
    if require_zero_fee and number(participant.get('fee_rate_bps', -1)) != 0:
        raise ReconciliationMismatch('Settlement fee evidence required')
    return dict(trade_id=trade['id'], quantity=qty,
                price=number(participant.get('price', -1), positive=True), fee=Decimal(0))


class LiveReconciler:
    def __init__(self, sessions, settlements=None):
        self.sessions = sessions
        self.journal = LiveOrderJournal(sessions)
        self.settlements = settlements

    async def _fills(self, gateway, associated, order, wallet):
        trades = [await gateway.trades_for_id(t) for t in associated]
        if self.settlements is None:
            return [confirmed_fill(t, order, wallet) for t in trades]
        # Several API matches can share one transaction. The receipt event is
        # the accounting identity; never charge its aggregate fee per API row.
        groups = {}
        for trade in trades:
            participant = confirmed_fill(trade, order, wallet, require_zero_fee=False)
            tx = trade.get('transaction_hash')
            if not isinstance(tx, str):
                raise ReconciliationMismatch('Trade settlement transaction unavailable')
            groups[tx.lower()] = groups.get(tx.lower(), Decimal(0)) + participant['quantity']
        fills = []
        for tx, quantity in groups.items():
            fill = await self.settlements.fill(tx, order, wallet)
            if fill['quantity'] != quantity:
                raise ReconciliationMismatch('API and receipt quantities disagree')
            fills.append(fill)
        return fills

    async def reconcile(self, user_id, gateway, signature_type):
        # A session advisory lock protects a whole remote-read cycle across replicas.
        async with self.sessions() as claim:
            if claim.bind.dialect.name != 'postgresql':
                raise RuntimeError('Live reconciliation requires PostgreSQL')
            key = int.from_bytes(uuid.UUID(str(user_id)).bytes[:8], 'big', signed=True)
            acquired = (await claim.execute(text('SELECT pg_try_advisory_lock(:key)'), {'key': key})).scalar()
            if not acquired:
                return {'status': 'BUSY'}
            try:
                return await self._reconcile(user_id, gateway, signature_type)
            finally:
                await claim.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': key})

    async def _reconcile(self, user_id, gateway, signature_type):
        attempt_id = uuid.uuid4()
        async with self.sessions() as db, db.begin():
            account = await self.journal._account(db, user_id)
            wallet, run_id = account.wallet_address, account.run_id
            account.reconciled_at = None  # No new submissions during a non-atomic remote snapshot.
            db.add(LiveReconciliation(id=attempt_id, user_id=user_id))
            orders = (await db.execute(select(LiveOrderIntent).where(
                LiveOrderIntent.user_id == user_id))).scalars().all()
            # Retain terminal orders in the audit: late conflicting fills must surface.
        try:
            async with asyncio.timeout(45):
                cancellation_failed = False
                for order in orders:
                    if order.cancel_requested_at is None:
                        continue
                    if order.state == 'PREPARED':
                        await self.journal.void_unsubmitted(user_id=user_id, order_id=order.id)
                    elif order.state not in ('VOID', 'CANCELLED', 'FILLED'):
                        try:
                            await gateway.cancel_order(order.signed_order_hash)
                        except Exception:
                            # Retain the request for the next cycle; reconcile other orders too.
                            cancellation_failed = True
                opened = await gateway.open_orders()
                known = {o.signed_order_hash.lower(): o for o in orders}
                for remote in opened:
                    order = known.get(str(remote.get('id', '')).lower())
                    if order is None or order.state in ('PREPARED', 'VOID'):
                        raise ReconciliationMismatch('Untracked exchange order')
                for order in orders:
                    if order.state in ('PREPARED', 'VOID'):
                        continue
                    remote = await gateway.get_order(order.signed_order_hash)
                    self._validate_order(remote, order, wallet)
                    associated = remote.get('associate_trades')
                    if not isinstance(associated, list) or len(set(associated)) != len(associated):
                        raise ReconciliationMismatch('Order trade coverage unavailable')
                    fills = await self._fills(gateway, associated, order, wallet)
                    matched = number(remote['size_matched'])
                    if sum((f['quantity'] for f in fills), Decimal(0)) != matched:
                        raise ReconciliationMismatch('Associated fills do not match order quantity')
                    for fill in fills:
                        await self.journal.record_confirmed_fill(user_id=user_id, order_id=order.id, **fill)
                    status = remote['status'].upper().removeprefix('ORDER_STATUS_')
                    if status in ('CANCELED', 'CANCELLED', 'EXPIRED'):
                        await self.journal.finalize_cancel(user_id=user_id, order_id=order.id,
                            reconciled_filled_quantity=matched, exchange_status=status)
                    elif status not in ('LIVE', 'MATCHED', 'FILLED'):
                        raise ReconciliationMismatch('Unsupported exchange order state')
                    elif status in ('MATCHED', 'FILLED') and matched != order.quantity:
                        raise ReconciliationMismatch('Terminal order has incomplete fills')
                    else:
                        async with self.sessions() as db, db.begin():
                            await self.journal._account(db, user_id)
                            stored = await db.get(LiveOrderIntent, order.id)
                            if stored.state in ('SUBMITTING', 'UNKNOWN'):
                                stored.state = 'ACKNOWLEDGED'
                if cancellation_failed:
                    raise ReconciliationMismatch('Cancellation request incomplete; retry pending')
                collateral = await gateway.collateral_balance(signature_type)
                cash = number(collateral['balance'])
                async with self.sessions() as db:
                    positions = (await db.execute(select(LivePosition).where(
                        LivePosition.user_id == user_id))).scalars().all()
                    baseline = await db.get(LiveWalletBaseline, user_id)
                if baseline is not None:
                    if self.settlements is None:
                        raise ReconciliationMismatch('Complete on-chain wallet coverage required')
                    from app.services.live_wallet_snapshot import LiveWalletSnapshot, CTF
                    snapshot = await LiveWalletSnapshot(self.settlements).read(wallet)
                    positive = {key:number(value) for key,value in snapshot['balances'].items() if number(value) > 0}
                    expected = {CTF+':'+p.token_id:p.quantity for p in positions if p.quantity > 0}
                    if positive != expected:
                        raise ReconciliationMismatch('Complete wallet inventory differs from journal')
                    if snapshot['cash'] != cash:
                        raise ReconciliationMismatch('Confirmed wallet cash differs from venue')
                balances = {p.token_id: await gateway.token_balance(p.token_id, signature_type) for p in positions}
                async with self.sessions() as db, db.begin():
                    account = await self.journal._account(db, user_id)
                    if account.run_id != run_id or account.wallet_address != wallet:
                        raise ReconciliationMismatch('Account changed during reconciliation')
                    if cash != account.cash:
                        raise ReconciliationMismatch('Collateral balance differs from journal')
                    current = (await db.execute(select(LivePosition).where(LivePosition.user_id == user_id))).scalars().all()
                    if {p.token_id: p.quantity for p in current} != balances:
                        raise ReconciliationMismatch('Token balances differ from journal')
                    if any(p.quantity < p.reserved_quantity or p.reserved_quantity < 0 for p in current):
                        raise ReconciliationMismatch('Invalid share reservation')
                    if not 0 <= account.reserved_cash <= account.cash:
                        raise ReconciliationMismatch('Invalid cash reservation')
                    account.reconciled_at = datetime.utcnow()
                    attempt = await db.get(LiveReconciliation, attempt_id)
                    attempt.status, attempt.finished_at, attempt.observed_cash = 'MATCHED', datetime.utcnow(), cash
                    # Successful reads never automatically undo a kill switch.
                return {'status': 'MATCHED'}
        except Exception as exc:
            async with self.sessions() as db, db.begin():
                account = await self.journal._account(db, user_id)
                waiting = isinstance(exc, SettlementPending)
                if not waiting:
                    account.enabled = False
                account.reconciled_at = None  # Waiting also prevents all new submissions.
                attempt = await db.get(LiveReconciliation, attempt_id)
                attempt.status, attempt.finished_at = 'WAITING' if waiting else 'BLOCKED', datetime.utcnow()
                # Provider exceptions may contain request metadata. Persist only our safe messages.
                attempt.detail = str(exc)[:255] if isinstance(exc, ReconciliationMismatch) else type(exc).__name__
            return {'status': attempt.status, 'reason': attempt.detail}

    @staticmethod
    def _validate_order(remote, order, wallet):
        if (str(remote.get('id', '')).lower() != order.signed_order_hash.lower()
                or remote.get('maker_address', '').lower() != wallet.lower()
                or remote.get('asset_id') != order.token_id or remote.get('side') != order.side
                or number(remote.get('original_size', -1)) != order.quantity
                or number(remote.get('price', -1)) != order.limit_price
                or number(remote.get('size_matched', -1)) > order.quantity):
            raise ReconciliationMismatch('Exchange order differs from signed intent')
