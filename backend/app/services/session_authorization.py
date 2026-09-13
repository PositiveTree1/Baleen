"""Owner-signed, fixed-purpose session grants. No owner private key is accepted.

Protocol: docs.polymarket.com/trading/session-keys; pinned SDK 0.10.0.
Unknown relayer outcomes are retained for verification, never blindly reposted.
"""
from datetime import datetime
import json
import re
import time
import uuid
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from sqlalchemy import select
try:
    from polymarket.auth import BuilderApiKey
    from polymarket._internal.actions.relayer.auth import build_builder_key_headers
    from polymarket._internal.actions.relayer.calls import authorize_session_signer_call, revoke_session_signer_call
    from polymarket._internal.actions.relayer.signing.deposit_wallet import build_deposit_wallet_typed_data
except ImportError:
    BuilderApiKey = None
    build_builder_key_headers = None
    authorize_session_signer_call = None
    revoke_session_signer_call = None
    build_deposit_wallet_typed_data = None
from app.config import settings
from app.models import User, LiveSigningSession, LiveWalletLink, LiveSessionOperation
from app.services.live_runtime import verify_owner_wallet

LIFETIME = 4315 * 60 * 60  # Venue-required lifetime; do not silently substitute another value.
RELAY = 'https://relayer-v2.polymarket.com'


def typed_data(operation):
    if operation.kind == 'AUTHORIZE':
        call = authorize_session_signer_call(wallet_address=operation.wallet_address,
            session_signer=operation.session_address, valid_until=operation.valid_until)
    elif operation.kind == 'REVOKE':
        call = revoke_session_signer_call(wallet_address=operation.wallet_address, session_signer=operation.session_address)
    else:
        raise ValueError('Unknown session operation')
    typed = build_deposit_wallet_typed_data(wallet=operation.wallet_address, calls=[call],
        nonce=operation.nonce, deadline=str(operation.deadline), chain_id=137)
    # Browser JSON must preserve full uint256 precision, including large nonces.
    typed['message']['nonce'] = str(typed['message']['nonce'])
    typed['message']['deadline'] = str(typed['message']['deadline'])
    for item in typed['message']['calls']:
        item['value'] = str(item['value'])
        item['data'] = '0x'+item['data'].hex()
    return typed


def public_operation(operation):
    return {'id':str(operation.id), 'kind':operation.kind, 'state':operation.state,
        'ownerAddress':operation.owner_address, 'walletAddress':operation.wallet_address,
        'sessionAddress':operation.session_address, 'deadline':operation.deadline,
        'validUntil':operation.valid_until, 'scopes':['CLOB'] if operation.kind == 'AUTHORIZE' else [],
        'transactionId':operation.transaction_id, 'transactionHash':operation.transaction_hash,
        'liveExecutionReady':False,
        'typedData':typed_data(operation) if operation.state == 'PREPARED' else None}


class SessionRelay:
    def __init__(self):
        if not all((settings.POLYMARKET_BUILDER_API_KEY, settings.POLYMARKET_BUILDER_SECRET,
                    settings.POLYMARKET_BUILDER_PASSPHRASE)):
            raise PermissionError('Approved builder credentials are not configured')
        self.credentials = BuilderApiKey(key=settings.POLYMARKET_BUILDER_API_KEY,
            secret=settings.POLYMARKET_BUILDER_SECRET, passphrase=settings.POLYMARKET_BUILDER_PASSPHRASE)

    async def nonce(self, owner):
        async with httpx.AsyncClient(base_url=RELAY, timeout=10, follow_redirects=False) as client:
            response = await client.get('/v1/account/transactions/params', params={'address':owner, 'type':'WALLET'})
            response.raise_for_status()
            value = response.json().get('nonce')
        if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)) or not 0 <= int(value) < 2**256:
            raise ValueError('Invalid wallet nonce')
        return str(value)

    async def submit(self, operation, signature):
        path = '/v1/session-signers/' + ('authorizations' if operation.kind == 'AUTHORIZE' else 'revocations')
        payload = {'walletAddress':operation.wallet_address, 'sessionSignerAddress':operation.session_address,
            'nonce':operation.nonce, 'deadline':str(operation.deadline), 'signature':signature}
        if operation.kind == 'AUTHORIZE':
            payload.update(scopes=['CLOB'], validUntil=str(operation.valid_until))
        body = json.dumps(payload, separators=(',', ':'))
        headers = build_builder_key_headers(creds=self.credentials, method='POST', path=path, body=body)
        headers.update({'Content-Type':'application/json', 'Idempotency-Key':str(operation.id)})
        async with httpx.AsyncClient(base_url=RELAY, timeout=15, follow_redirects=False) as client:
            response = await client.post(path, content=body, headers=headers)
            response.raise_for_status()
            return response.json()


class SessionAuthorization:
    def __init__(self, sessions, relay, owner_check=verify_owner_wallet):
        self.sessions, self.relay, self.owner_check = sessions, relay, owner_check

    async def prepare(self, user_id, kind):
        if kind not in ('AUTHORIZE', 'REVOKE'):
            raise ValueError('Unsupported session operation')
        async with self.sessions() as db, db.begin():
            await db.execute(select(User).where(User.id == user_id).with_for_update())
            session, link = await db.get(LiveSigningSession, user_id), await db.get(LiveWalletLink, user_id)
            if (session is None or link is None or link.signature_type != 3
                    or session.wallet_address != link.polymarket_wallet_address.lower()
                    or (kind == 'AUTHORIZE' and session.revoked_at is not None)):
                raise PermissionError('Active Deposit Wallet session setup required')
            await self.owner_check(link)
            pending = (await db.execute(select(LiveSessionOperation).where(LiveSessionOperation.user_id == user_id,
                LiveSessionOperation.kind == kind, LiveSessionOperation.state.in_(['PREPARED','SUBMITTING','UNKNOWN','PENDING'])))).scalars().all()
            for old in pending:
                if old.state == 'PREPARED' and old.deadline <= time.time()+30:
                    old.state = 'EXPIRED'
                else:
                    return public_operation(old)  # Same challenge/outcome, never fresh permission on a retry.
            nonce = await self.relay.nonce(link.signer_address)
            now = int(time.time())
            operation = LiveSessionOperation(id=uuid.uuid4(), user_id=user_id, kind=kind,
                owner_address=link.signer_address.lower(), wallet_address=session.wallet_address,
                session_address=session.session_address, nonce=nonce, deadline=now+300,
                valid_until=now+LIFETIME if kind == 'AUTHORIZE' else None, state='PREPARED')
            db.add(operation)
            return public_operation(operation)

    async def submit(self, user_id, operation_id, signature):
        async with self.sessions() as db, db.begin():
            await db.execute(select(User).where(User.id == user_id).with_for_update())
            operation = await db.get(LiveSessionOperation, operation_id)
            if operation is None or operation.user_id != user_id:
                raise PermissionError('Session operation not found')
            if operation.state != 'PREPARED':
                return public_operation(operation)
            session, link = await db.get(LiveSigningSession, user_id), await db.get(LiveWalletLink, user_id)
            if (session is None or link is None or session.session_address != operation.session_address
                    or session.wallet_address != operation.wallet_address or link.signer_address.lower() != operation.owner_address
                    or (operation.kind == 'AUTHORIZE' and session.revoked_at is not None)
                    or operation.deadline <= time.time()+30):
                raise PermissionError('Session operation expired or setup changed')
            if not isinstance(signature, str) or not re.fullmatch(r'0x[0-9a-fA-F]{130}', signature):
                raise ValueError('Expected an owner EIP-712 signature')
            signer = Account.recover_message(encode_typed_data(full_message=typed_data(operation)), signature=signature)
            if signer.lower() != operation.owner_address:
                raise PermissionError('Signature does not belong to the Deposit Wallet owner')
            if operation.kind == 'REVOKE':
                from app.api.live_trading import _disable_order_account
                await _disable_order_account(db, user_id)
                session.revoked_at, session.verified_at = datetime.utcnow(), None
            operation.state = 'SUBMITTING'
            operation.signature_hash = '0x'+keccak(bytes.fromhex(signature[2:])).hex()
        # The durable boundary above precedes network I/O. No key/signature in logs.
        try:
            response = await self.relay.submit(operation, signature)
            accepted = {'SUBMITTED','REGISTRY_PENDING','REGISTERED','PENDING','FENCED','SWEPT','CHAIN_SUBMITTED','CONFIRMED'}
            if not isinstance(response, dict) or response.get('status') not in accepted:
                raise ValueError('Relayer outcome requires verification')
            txid, txhash = response.get('transactionId'), response.get('transactionHash')
            if not isinstance(txid, str) or not 0 < len(txid) <= 255:
                raise ValueError('Relayer transaction identity unavailable')
            if txhash is not None and not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(txhash)):
                raise ValueError('Relayer transaction hash invalid')
        except Exception:
            async with self.sessions() as db, db.begin():
                row = await db.get(LiveSessionOperation, operation_id, with_for_update=True)
                if row.state == 'SUBMITTING':
                    row.state = 'UNKNOWN'
            raise PermissionError('Relayer outcome uncertain; verify this operation before attempting another') from None
        async with self.sessions() as db, db.begin():
            row = await db.get(LiveSessionOperation, operation_id, with_for_update=True)
            if row.state == 'SUBMITTING':
                row.state = 'PENDING'
            row.transaction_id, row.transaction_hash = txid, txhash
            return public_operation(row)  # Accepted submission is not proof of an active/revoked grant.
