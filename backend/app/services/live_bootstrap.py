"""Initialize a live journal only from actual, fully observed wallet balances."""
from datetime import datetime
from decimal import Decimal
import uuid
from sqlalchemy import select
from app.models import User, LiveSigningSession, LiveExecutionAccount, LiveWalletBaseline


class LiveBootstrap:
    def __init__(self, sessions, runtime, wallet_reader):
        self.sessions, self.runtime, self.wallet_reader = sessions, runtime, wallet_reader

    async def initialize(self, user_id):
        async with self.sessions() as db, db.begin():
            if db.bind.dialect.name != 'postgresql':
                raise PermissionError('Live account initialization requires PostgreSQL')
            await db.execute(select(User).where(User.id == user_id).with_for_update())
            account = await db.get(LiveExecutionAccount, user_id)
            if account is not None:
                baseline = await db.get(LiveWalletBaseline, user_id)
                if baseline is None or baseline.run_id != account.run_id:
                    raise PermissionError('Existing account has no verified baseline; operator reconciliation required')
                return {'runId':str(account.run_id), 'startingCash':str(baseline.starting_cash),
                    'blockNumber':baseline.block_number, 'liveExecutionReady':False}
            session = await db.get(LiveSigningSession, user_id)
            if (session is None or session.revoked_at is not None or session.verified_at is None
                    or session.session_address != self.runtime.signer.session_address):
                raise PermissionError('Owner-approved session verification required')
            await self.runtime.signer.verify_authorization()
            if await self.runtime.owner_gateway.open_orders() or await self.runtime.gateway.open_orders():
                raise PermissionError('Existing venue orders require reconciliation before initializing')
            snapshot = await self.wallet_reader.read(session.wallet_address)
            if any(Decimal(quantity) != 0 for quantity in snapshot['balances'].values()):
                raise PermissionError('Existing wallet positions require a verified cost-basis import; no basis will be invented')
            venue = await self.runtime.owner_gateway.collateral_balance(3)
            if Decimal(venue['balance']) != snapshot['cash']:
                raise PermissionError('Venue collateral differs from confirmed wallet funding')
            # Catch an owner action during the wallet snapshot.
            if await self.runtime.owner_gateway.open_orders() or await self.runtime.gateway.open_orders():
                raise PermissionError('Venue orders changed during initialization')
            await self.runtime.signer.verify_authorization()
            run = uuid.uuid4()
            account = LiveExecutionAccount(user_id=user_id, run_id=run, wallet_address=session.wallet_address,
                cash=snapshot['cash'], reserved_cash=0, enabled=False, reconciled_at=None)
            db.add(account)
            await db.flush()
            db.add(LiveWalletBaseline(user_id=user_id, run_id=run, block_number=snapshot['block_number'],
                block_hash=snapshot['block_hash'], block_time=snapshot['block_time'],
                starting_cash=snapshot['cash'], observed_tokens=list(snapshot['balances']), created_at=datetime.utcnow()))
            return {'runId':str(run), 'startingCash':str(snapshot['cash']), 'blockNumber':snapshot['block_number'],
                'liveExecutionReady':False}
