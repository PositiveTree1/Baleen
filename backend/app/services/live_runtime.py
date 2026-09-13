"""Construct session-only signing clients from account-bound encrypted material."""
from contextlib import asynccontextmanager
import json
from types import SimpleNamespace
import httpx
from eth_account import Account
try:
    from polymarket import AsyncSecureClient
except ImportError:
    AsyncSecureClient = None
from app.auth import decrypt_secret
from app.config import settings
from app.models import LiveSigningSession, LiveWalletLink
from app.services.clob_gateway import ClobCredentials, ClobGateway
from app.services.scoped_signer import ScopedOrderSigner


def decode_session_key(record):
    if not record.encrypted_key.startswith('v1:'):
        raise PermissionError('Session signing material must be encrypted')
    payload = json.loads(decrypt_secret(record.encrypted_key))
    if (payload.get('purpose') != 'baleen-clob-session' or payload.get('user_id') != str(record.user_id)
            or payload.get('wallet') != record.wallet_address or record.revoked_at is not None):
        raise PermissionError('Session key account binding mismatch')
    key = payload['key']
    if Account.from_key(key).address.lower() != record.session_address:
        raise PermissionError('Session key identity mismatch')
    return key


async def verify_owner_wallet(link):
    """Authenticate wallet identity before reserving it for an application user."""
    if settings.CLOB_API_URL.rstrip('/') != 'https://clob.polymarket.com':
        raise PermissionError('Unreviewed exchange endpoint')
    credentials = ClobCredentials(link.signer_address or '', decrypt_secret(link.clob_api_key_enc),
        decrypt_secret(link.clob_api_secret_enc), decrypt_secret(link.clob_api_passphrase_enc))
    async with httpx.AsyncClient(base_url=settings.CLOB_API_URL, timeout=10, follow_redirects=False) as http:
        response = await ClobGateway(credentials, http)._get('/v1/user/session-signers')
    if (not isinstance(response, dict) or response.get('wallet', '').lower() != link.polymarket_wallet_address.lower()
            or not isinstance(response.get('signers'), list)):
        raise PermissionError('Owner-authenticated Deposit Wallet identity mismatch')


@asynccontextmanager
async def live_runtime(sessions, user_id):
    async with sessions() as db:
        record = await db.get(LiveSigningSession, user_id)
        link = await db.get(LiveWalletLink, user_id)
        if (record is None or link is None or link.signature_type != 3
                or record.wallet_address != (link.polymarket_wallet_address or '').lower()):
            raise PermissionError('Deposit Wallet session onboarding required')
        key = decode_session_key(record)
        owner_credentials = ClobCredentials(link.signer_address or '', decrypt_secret(link.clob_api_key_enc),
            decrypt_secret(link.clob_api_secret_enc), decrypt_secret(link.clob_api_passphrase_enc))
    if settings.CLOB_API_URL.rstrip('/') != 'https://clob.polymarket.com':
        raise PermissionError('Scoped SDK runtime requires the reviewed production exchange')
    async with httpx.AsyncClient(base_url=settings.CLOB_API_URL, timeout=10, follow_redirects=False) as http:
        owner = ClobGateway(owner_credentials, http)
        probe_client = SimpleNamespace(wallet_type='DEPOSIT_WALLET', wallet=record.wallet_address,
                                       signer=record.session_address)
        probe_gateway = SimpleNamespace(credentials=SimpleNamespace(signer_address=record.session_address))
        probe = ScopedOrderSigner(probe_client, owner, probe_gateway, wallet=record.wallet_address,
                                  session_address=record.session_address)
        await probe.verify_authorization()  # No key derivation until owner grant is present.
        client = await AsyncSecureClient.create(private_key=key, wallet=record.wallet_address)
        try:
            creds = client.credentials
            gateway = ClobGateway(ClobCredentials(record.session_address, creds.key, creds.secret, creds.passphrase), http)
            signer = ScopedOrderSigner(client, owner, gateway, wallet=record.wallet_address,
                                       session_address=record.session_address)
            await signer.verify_authorization()
            yield SimpleNamespace(signer=signer, gateway=gateway, owner_gateway=owner, http=http)
        finally:
            await client.close()
