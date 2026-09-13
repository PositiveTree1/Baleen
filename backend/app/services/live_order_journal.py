"""Durable live order reservations and fill reconciliation.

No worker or endpoint automatically submits these orders. A verified signer,
wallet binding and approved risk policy must supply the exact signed envelope.
All financial mutations are scoped to one locked account transaction.
"""
from datetime import datetime
from decimal import Decimal
import re
from sqlalchemy import select
from app.models import LiveExecutionAccount, LiveOrderIntent, LivePosition, LiveConfirmedFill, LiveSourcePosition
from app.services.clob_gateway import SubmissionUncertain


def number(value, *, positive=False):
    n = Decimal(str(value))
    if not n.is_finite() or n < 0 or (positive and n == 0):
        raise ValueError('Invalid financial quantity')
    return n


class LiveOrderJournal:
    def __init__(self, sessions, submission_gate=None):
        self.sessions = sessions
        self.submission_gate = submission_gate

    @staticmethod
    def _require_fresh_account(account):
        age = ((datetime.utcnow() - account.reconciled_at).total_seconds()
               if account.reconciled_at is not None else None)
        if not account.enabled or age is None or not 0 <= age <= 30:
            raise PermissionError('Account disabled or balance reconciliation stale')

    async def _account(self, db, user_id):
        account = (await db.execute(select(LiveExecutionAccount).where(
            LiveExecutionAccount.user_id == user_id).with_for_update())).scalar_one_or_none()
        if account is None:
            raise ValueError('No reconciled live account')
        return account

    async def prepare(self, *, user_id, run_id, intent_key, token_id, side, quantity,
                      limit_price, fee_budget, signed_order_hash, envelope, risk_context=None):
        qty, price, fee = number(quantity, positive=True), number(limit_price, positive=True), number(fee_budget)
        if price >= 1 or side not in ('BUY', 'SELL') or not re.fullmatch(r'[0-9]+', token_id):
            raise ValueError('Invalid token/side/limit price')
        if not intent_key or not re.fullmatch(r'0x[0-9a-fA-F]{64}', signed_order_hash):
            raise ValueError('Stable intent key and signed order hash are required')
        signed_order_hash = signed_order_hash.lower()
        signed = envelope.get('order', {})
        raw_shares, raw_cash = qty * 1000000, qty * price * 1000000
        if raw_shares != raw_shares.to_integral_value() or raw_cash != raw_cash.to_integral_value():
            raise ValueError('Order precision exceeds raw venue units')
        maker_amount, taker_amount = (raw_cash, raw_shares) if side == 'BUY' else (raw_shares, raw_cash)
        if (str(signed.get('tokenId')) != token_id or signed.get('side') != side
                or number(signed.get('makerAmount', -1)) != maker_amount
                or number(signed.get('takerAmount', -1)) != taker_amount or not signed.get('signature')):
            raise ValueError('Signed payload does not match the reserved intent')
        async with self.sessions() as db, db.begin():
            account = await self._account(db, user_id)
            if account.run_id != run_id:
                raise ValueError('Wrong account run')
            if str(signed.get('maker', '')).lower() != account.wallet_address.lower():
                raise ValueError('Signed maker is not this account wallet')
            existing = (await db.execute(select(LiveOrderIntent).where(
                LiveOrderIntent.user_id == user_id, LiveOrderIntent.run_id == run_id,
                LiveOrderIntent.intent_key == intent_key))).scalar_one_or_none()
            if existing:
                if (existing.signed_order_hash != signed_order_hash or existing.envelope != envelope
                        or existing.fee_budget != fee or existing.risk_context != risk_context):
                    raise ValueError('Conflicting replay of live intent')
                return existing.id
            self._require_fresh_account(account)
            reserve = qty * price + fee if side == 'BUY' else Decimal(0)
            if side == 'BUY':
                if account.cash - account.reserved_cash < reserve:
                    raise ValueError('Insufficient unreserved cash including fees')
                account.reserved_cash += reserve
            else:
                position = await db.get(LivePosition, (user_id, token_id))
                if not position or position.quantity - position.reserved_quantity < qty:
                    raise ValueError('Insufficient unreserved shares')
                position.reserved_quantity += qty
                if risk_context:
                    source = risk_context['source_wallet']
                    allocated = await db.get(LiveSourcePosition, (user_id, source, token_id))
                    pending = (await db.execute(select(LiveOrderIntent).where(
                        LiveOrderIntent.user_id == user_id, LiveOrderIntent.token_id == token_id,
                        LiveOrderIntent.side == 'SELL', LiveOrderIntent.state.in_(
                            ['PREPARED','SUBMITTING','UNKNOWN','ACKNOWLEDGED','PARTIAL'])))).scalars().all()
                    reserved = sum((o.quantity-o.filled_quantity for o in pending
                        if o.risk_context and o.risk_context.get('source_wallet') == source), Decimal(0))
                    if allocated is None or qty > allocated.quantity - reserved:
                        raise ValueError('Insufficient shares attributable to this source wallet')
            order = LiveOrderIntent(user_id=user_id, run_id=run_id, intent_key=intent_key,
                token_id=token_id, side=side, quantity=qty, limit_price=price, fee_budget=fee,
                filled_quantity=0, reserved_cash=reserve, state='PREPARED',
                signed_order_hash=signed_order_hash, envelope=envelope, risk_context=risk_context)
            db.add(order)
            await db.flush()
            return order.id

    async def submit(self, *, user_id, order_id, gateway):
        async with self.sessions() as db, db.begin():
            account = await self._account(db, user_id)
            order = await db.get(LiveOrderIntent, order_id)
            if not order or order.user_id != user_id or order.run_id != account.run_id:
                raise ValueError('Order scope mismatch')
            self._require_fresh_account(account)
            if order.state != 'PREPARED':
                raise ValueError('Previously submitted or uncertain order; reconcile instead of resending')
            if order.cancel_requested_at is not None:
                raise PermissionError('Cancellation was requested for this intent')
            if self.submission_gate is None or await self.submission_gate(db, account, order) is not True:
                raise PermissionError('Verified signing authority and current risk approval required')
            # The gate may await venue reads. Recheck freshness before committing.
            self._require_fresh_account(account)
            order.state = 'SUBMITTING'
            envelope, expected_hash = order.envelope, order.signed_order_hash
        # Commit before I/O. A crash here leaves SUBMITTING, never a fresh retry.
        try:
            result = await gateway.submit_signed_order(envelope, submission_authorized=True)
            if str(result.get('orderID', '')).lower() != expected_hash.lower():
                raise SubmissionUncertain('Exchange acknowledgement identity mismatch')
        except Exception:
            async with self.sessions() as db, db.begin():
                await self._account(db, user_id)
                order = await db.get(LiveOrderIntent, order_id)
                # A fill may have arrived concurrently; do not erase that progress.
                if order.state == 'SUBMITTING':
                    order.state = 'UNKNOWN'
            raise
        async with self.sessions() as db, db.begin():
            await self._account(db, user_id)
            order = await db.get(LiveOrderIntent, order_id)
            if order.state == 'SUBMITTING':
                order.state = 'ACKNOWLEDGED'
        return result

    async def record_confirmed_fill(self, *, user_id, order_id, trade_id, quantity, price, fee, cash_amount=None):
        qty, px, charge = number(quantity, positive=True), number(price, positive=True), number(fee)
        if px > 1 or not trade_id:
            raise ValueError('Invalid confirmed fill')
        cash = qty * px if cash_amount is None else number(cash_amount, positive=True)
        if abs(cash - qty * px) > Decimal('0.000000000001'):
            raise ValueError('Settlement cash and price disagree')
        async with self.sessions() as db, db.begin():
            account = await self._account(db, user_id)
            order = await db.get(LiveOrderIntent, order_id)
            if not order or order.user_id != user_id:
                raise ValueError('Fill scope mismatch')
            old = await db.get(LiveConfirmedFill, (order_id, trade_id))
            if old:
                if (old.quantity != qty or old.fee != charge
                        or (old.cash_amount if old.cash_amount is not None else old.quantity * old.price) != cash):
                    raise ValueError('Conflicting confirmed fill')
                return False
            if order.state not in ('SUBMITTING', 'UNKNOWN', 'ACKNOWLEDGED', 'PARTIAL'):
                raise ValueError('Order state cannot accept another fill')
            if qty + order.filled_quantity > order.quantity:
                raise ValueError('Confirmed quantity exceeds signed order')
            position = await db.get(LivePosition, (user_id, order.token_id))
            if position is None:
                position = LivePosition(user_id=user_id, token_id=order.token_id,
                                        quantity=0, reserved_quantity=0, cost_basis=0)
                db.add(position)
            realized = None
            if order.side == 'BUY':
                cost = cash + charge
                allocation = min(order.reserved_cash, qty * order.limit_price + order.fee_budget * qty / order.quantity)
                account.cash -= cost
                account.reserved_cash -= allocation
                order.reserved_cash -= allocation
                position.quantity += qty
                position.cost_basis += cost
                if px > order.limit_price or cost > allocation or account.cash < account.reserved_cash:
                    # Record real money movement; halt new risk instead of hiding a discrepancy.
                    account.enabled = False
            else:
                if qty > position.quantity or qty > position.reserved_quantity:
                    raise ValueError('Fill exceeds reserved inventory')
                basis = position.cost_basis * qty / position.quantity
                realized = cash - charge - basis
                position.cost_basis -= basis
                position.quantity -= qty
                position.reserved_quantity -= qty
                account.cash += cash - charge
                if (px < order.limit_price or charge > order.fee_budget * qty / order.quantity
                        or account.cash < account.reserved_cash):
                    account.enabled = False
            if order.risk_context:
                source = order.risk_context['source_wallet']
                allocation = await db.get(LiveSourcePosition, (user_id, source, order.token_id))
                if allocation is None:
                    if order.side == 'SELL':
                        raise ValueError('Missing source inventory for confirmed exit')
                    allocation = LiveSourcePosition(user_id=user_id, source_wallet_address=source,
                        token_id=order.token_id, quantity=0)
                    db.add(allocation)
                if order.side == 'SELL' and allocation.quantity < qty:
                    raise ValueError('Confirmed exit exceeds source inventory')
                allocation.quantity += qty if order.side == 'BUY' else -qty
            order.filled_quantity += qty
            order.state = 'FILLED' if order.filled_quantity == order.quantity else 'PARTIAL'
            if order.state == 'FILLED' and order.reserved_cash:
                account.reserved_cash -= order.reserved_cash
                order.reserved_cash = 0
            db.add(LiveConfirmedFill(order_id=order_id, trade_id=trade_id, quantity=qty, price=px,
                                    fee=charge, cash_amount=cash, realized_pnl=realized))
            return True

    async def finalize_cancel(self, *, user_id, order_id, reconciled_filled_quantity, exchange_status):
        """Call only after authenticated terminal status AND complete fill reconciliation."""
        if exchange_status not in ('CANCELED', 'CANCELLED', 'EXPIRED'):
            raise ValueError('Exchange has not confirmed a terminal cancellation')
        async with self.sessions() as db, db.begin():
            account = await self._account(db, user_id)
            order = await db.get(LiveOrderIntent, order_id)
            if not order or order.user_id != user_id:
                raise ValueError('Order scope mismatch')
            if order.state in ('CANCELLED', 'FILLED'):
                return
            if order.filled_quantity != number(reconciled_filled_quantity):
                raise ValueError('Cannot release reservations before all fills are reconciled')
            account.reserved_cash -= order.reserved_cash
            order.reserved_cash = 0
            if order.side == 'SELL':
                position = await db.get(LivePosition, (user_id, order.token_id))
                position.reserved_quantity -= order.quantity - order.filled_quantity
            order.state = 'CANCELLED'

    async def void_unsubmitted(self, *, user_id, order_id):
        """Release only an explicitly stopped order proven never to have reached I/O."""
        async with self.sessions() as db, db.begin():
            account = await self._account(db, user_id)
            order = await db.get(LiveOrderIntent, order_id)
            if not order or order.user_id != user_id:
                raise ValueError('Order scope mismatch')
            if order.state != 'PREPARED' or order.cancel_requested_at is None:
                return False
            account.reserved_cash -= order.reserved_cash
            order.reserved_cash = 0
            if order.side == 'SELL':
                position = await db.get(LivePosition, (user_id, order.token_id))
                position.reserved_quantity -= order.quantity
            order.state = 'VOID'
            return True
