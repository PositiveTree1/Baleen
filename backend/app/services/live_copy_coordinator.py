"""Connect persisted source evidence, policy, session signing and the live journal.

No HTTP endpoint accepts arbitrary trade envelopes. The account's current policy
and source allocation are re-read under the journal lock immediately before I/O.
"""
from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_CEILING
import time
import uuid
from sqlalchemy import select, text
try:
    from polymarket.models.clob.orders import SignedOrder
except ImportError:
    from dataclasses import dataclass
    @dataclass
    class SignedOrder:
        builder: str = ""
        expiration: int = 0
        maker: str = ""
        maker_amount: int = 0
        metadata: str = ""
        order_type: str = ""
        salt: int = 0
        side: str = ""
        signature_type: int = 0
        signer: str = ""
        taker_amount: int = 0
        timestamp: int = 0
        token_id: str = ""
        signature: str = ""
        post_only: bool = False
from app.models import (CanonicalSourceEvent, LiveCopyPolicy, LiveSigningSession,
    LiveOrderIntent, LiveExecutionAccount, LivePosition, LiveSourcePosition, LiveConfirmedFill, LiveWalletBaseline)
from app.services.live_order_journal import LiveOrderJournal, number
from app.services.live_risk import RiskLimits, RiskRejected, check_live_order
from app.services.scoped_signer import verify_session_order, EXCHANGES
from app.sizing.proportional import proportional_quantity
from app.services.wallet_eligibility import require_research_approval

PENDING = ['PREPARED','SUBMITTING','UNKNOWN','ACKNOWLEDGED','PARTIAL']
INTEGER_LIMITS = {'max_open_orders','max_quote_age_ms','max_source_age_ms'}


def policy_limits(policy):
    values = {f.name: policy.limits[f.name] if f.name in INTEGER_LIMITS else number(policy.limits[f.name])
              for f in fields(RiskLimits)}
    limits = RiskLimits(**values)
    limits.validate()
    return limits


def signed_from_envelope(envelope):
    wire = envelope['order']
    return SignedOrder(builder=wire['builder'], expiration=int(wire['expiration']), maker=wire['maker'],
        maker_amount=int(wire['makerAmount']), metadata=wire['metadata'], order_type=envelope['orderType'],
        salt=int(wire['salt']), side=wire['side'], signature_type=int(wire['signatureType']),
        signer=wire['signer'], taker_amount=int(wire['takerAmount']), timestamp=int(wire['timestamp']),
        token_id=wire['tokenId'], signature=wire['signature'], post_only=envelope.get('postOnly', False))


class LiveCopyCoordinator:
    def __init__(self, sessions, runtime, market_evidence):
        self.sessions, self.runtime, self.market_evidence = sessions, runtime, market_evidence
        self.journal = LiveOrderJournal(sessions, submission_gate=self.submission_gate)

    async def submission_gate(self, db, account, order):
        context = order.risk_context or {}
        policy = await db.get(LiveCopyPolicy, account.user_id)
        source = await db.get(CanonicalSourceEvent, uuid.UUID(context['source_event_id']))
        session = await db.get(LiveSigningSession, account.user_id)
        baseline = await db.get(LiveWalletBaseline, account.user_id)
        if (baseline is None or baseline.run_id != account.run_id or source is None
                or source.block_time is None or source.block_time < baseline.created_at):
            raise RiskRejected('Source predates a verified account baseline')
        if (policy is None or policy.revision != context.get('policy_revision') or session is None
                or session.revoked_at is not None or session.wallet_address != account.wallet_address.lower()
                or session.session_address != self.runtime.signer.session_address):
            raise RiskRejected('Policy or signing session changed')
        if (source is None or source.status not in ('CONFIRMED','APPLIED') or source.chain_id != 137
                or source.block_time is None or source.log_index is None or source.block_hash is None
                or source.emitting_contract is None or source.emitting_contract.lower() not in EXCHANGES
                or source.source_wallet_address.lower() != context.get('source_wallet')
                or source.token_id != order.token_id or source.side != order.side):
            raise RiskRejected('Canonical source evidence mismatch')
        if source.side == 'BUY' and source.source_wallet_address.lower() not in policy.source_wallets:
            raise RiskRejected('Source removed from account copy policy')
        if source.block_time < policy.updated_at:
            raise RiskRejected('Source predates the approved copy policy')
        proof = await self.market_evidence.source(source)
        await require_research_approval(db, source.source_wallet_address, source.side)
        approved_quantity = proportional_quantity(proof['quantity'], policy.copy_ratio)
        if order.quantity > approved_quantity:
            raise RiskRejected('Order exceeds verified source allocation')
        limits = policy_limits(policy)
        observed = await self.market_evidence.market(source.condition_id, order.token_id)
        signed = signed_from_envelope(order.envelope)
        if (signed.order_type != 'GTD' or signed.expiration <= time.time() + 60
                or signed.expiration > time.time() + 300 or order.envelope.get('deferExec') is not False
                or order.envelope.get('owner') != self.runtime.gateway.credentials.api_key):
            raise RiskRejected('Expired or changed order wire policy')
        recovered = verify_session_order(signed, wallet=account.wallet_address,
            session_address=session.session_address, exchange_address=observed['exchange'])
        if recovered != order.signed_order_hash:
            raise RiskRejected('Signed hash differs from reserved intent')
        pending = (await db.execute(select(LiveOrderIntent).where(LiveOrderIntent.user_id == account.user_id,
            LiveOrderIntent.state.in_(PENDING), LiveOrderIntent.id != order.id))).scalars().all()
        positions = (await db.execute(select(LivePosition).where(LivePosition.user_id == account.user_id))).scalars().all()
        source_position = await db.get(LiveSourcePosition, (account.user_id, source.source_wallet_address.lower(), order.token_id))
        source_reserved = sum((p.quantity-p.filled_quantity for p in pending if p.side == 'SELL'
            and p.token_id == order.token_id and p.risk_context
            and p.risk_context.get('source_wallet') == source.source_wallet_address.lower()), Decimal(0))
        source_shares = (source_position.quantity if source_position else Decimal(0)) - source_reserved
        loss = Decimal(0)
        if order.side == 'BUY':
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            realized = (await db.execute(select(LiveConfirmedFill.realized_pnl).join(LiveOrderIntent,
                LiveOrderIntent.id == LiveConfirmedFill.order_id).where(LiveOrderIntent.user_id == account.user_id,
                LiveConfirmedFill.confirmed_at >= today))).scalars().all()
            loss = sum((-v for v in realized if v is not None and v < 0), Decimal(0))
            for position in positions:
                if position.quantity:
                    bid = await self.market_evidence.mark(position.token_id, limits.max_quote_age_ms)
                    loss += max(Decimal(0), position.cost_basis-position.quantity*bid)
        fee_cap = number(observed['fee_cap_bps'])
        if fee_cap > number(policy.limits['max_fee_bps']):
            raise RiskRejected('Venue maximum fee exceeds approved account limit')
        cash_bound = order.quantity * (order.limit_price if order.side == 'BUY' else Decimal(1))
        required_fee = (cash_bound * fee_cap / 10000).quantize(Decimal('.000001'), rounding=ROUND_CEILING)
        if order.fee_budget < required_fee:
            raise RiskRejected('Reserved fee budget is insufficient')
        total_exposure = sum((p.cost_basis for p in positions), Decimal(0)) + sum((p.reserved_cash for p in pending), Decimal(0))
        token_exposure = sum((p.cost_basis for p in positions if p.token_id == order.token_id), Decimal(0)) + sum(
            (p.reserved_cash for p in pending if p.token_id == order.token_id), Decimal(0))
        timestamp = int(source.block_time.replace(tzinfo=timezone.utc).timestamp()*1000)
        check_live_order(limits=limits, side=order.side, token_id=order.token_id, quantity=order.quantity,
            limit_price=order.limit_price, fee_budget=order.fee_budget, source_price=proof['price'],
            source_timestamp_ms=timestamp, now_ms=int(time.time()*1000), book=observed['book'],
            accepting_orders=observed['accepting_orders'], available_cash=account.cash-account.reserved_cash+order.reserved_cash,
            available_shares=max(Decimal(0), source_shares), total_exposure=total_exposure, token_exposure=token_exposure,
            daily_loss=loss, open_order_count=len(pending))
        await self.runtime.signer.verify_authorization()
        return True

    async def copy_source(self, user_id, source_id):
        # Serializes source-to-intent creation across workers; account locks still
        # protect prepare, submission, reconciliation and stop independently.
        async with self.sessions() as claim:
            if claim.bind.dialect.name != 'postgresql':
                raise RuntimeError('Live copying requires PostgreSQL')
            key = int.from_bytes(uuid.UUID(str(user_id)).bytes[8:], 'big', signed=True)
            if not (await claim.execute(text('SELECT pg_try_advisory_xact_lock(:key)'), {'key':key})).scalar():
                return None
            async with self.sessions() as db:
                account = await db.get(LiveExecutionAccount, user_id)
                if account is None:
                    raise RiskRejected('No bootstrapped account')
                baseline = await db.get(LiveWalletBaseline, user_id)
                if baseline is None or baseline.run_id != account.run_id:
                    raise RiskRejected('Verified wallet baseline missing')
                self.journal._require_fresh_account(account)
                source, policy = await db.get(CanonicalSourceEvent, source_id), await db.get(LiveCopyPolicy, user_id)
                if source is None or policy is None:
                    raise RiskRejected('Source or policy missing')
                await require_research_approval(db, source.source_wallet_address, source.side)
                if source.block_time is None or source.block_time < max(policy.updated_at, baseline.created_at):
                    raise RiskRejected('Source predates the approved copy policy')
                intent_key = 'source:' + str(source_id)
                old = (await db.execute(select(LiveOrderIntent).where(LiveOrderIntent.user_id == user_id,
                    LiveOrderIntent.run_id == account.run_id, LiveOrderIntent.intent_key == intent_key))).scalar_one_or_none()
                if old:
                    if old.state == 'PREPARED':
                        old_id = old.id
                        await db.close()
                        return await self._submit_or_void(user_id, old_id)
                    return old.id  # Never re-sign an uncertain, rejected or completed source event.
                observed = await self.market_evidence.market(source.condition_id, source.token_id)
                book = observed['book']
                prices = [number(r['price'], positive=True) for r in book['asks' if source.side == 'BUY' else 'bids']]
                if not prices:
                    raise RiskRejected('No current liquidity')
                price = min(prices) if source.side == 'BUY' else max(prices)
                proof = await self.market_evidence.source(source)
                quantity = proportional_quantity(proof['quantity'], policy.copy_ratio)
                proportional_target = quantity
                if source.side == 'SELL':
                    allocation = await db.get(LiveSourcePosition, (user_id, source.source_wallet_address.lower(), source.token_id))
                    quantity = min(quantity, allocation.quantity if allocation else Decimal(0))
                if quantity <= 0:
                    raise RiskRejected('No eligible source quantity')
                cash_bound = quantity*(price if source.side == 'BUY' else Decimal(1))
                fee = (cash_bound*number(observed['fee_cap_bps'])/10000).quantize(Decimal('.000001'), rounding=ROUND_CEILING)
                context = {'source_event_id': str(source.id), 'source_wallet': source.source_wallet_address.lower(),
                           'policy_revision': policy.revision, 'copy_ratio': str(policy.copy_ratio),
                           'proportional_target': str(proportional_target),
                           'allocation_limited_exit': quantity != proportional_target}
                run_id = account.run_id
            signed = await self.runtime.signer.sign_limit(token_id=source.token_id, side=source.side,
                quantity=quantity, price=price, exchange_address=observed['exchange'])
            oid = await self.journal.prepare(user_id=user_id, run_id=run_id, intent_key=intent_key,
                token_id=source.token_id, side=source.side, quantity=quantity, limit_price=price, fee_budget=fee,
                signed_order_hash=signed['signed_order_hash'], envelope=signed['envelope'], risk_context=context)
            return await self._submit_or_void(user_id, oid)

    async def _submit_or_void(self, user_id, oid):
        try:
            return await self.journal.submit(user_id=user_id, order_id=oid, gateway=self.runtime.gateway)
        except Exception:
            async with self.sessions() as db, db.begin():
                await self.journal._account(db, user_id)
                order = await db.get(LiveOrderIntent, oid)
                if order.state == 'PREPARED':
                    order.cancel_requested_at = datetime.utcnow()
            await self.journal.void_unsubmitted(user_id=user_id, order_id=oid)
            raise
