"""Deposit Wallet session signing adapter, pinned to polymarket-client 0.10.0.

Only signs; it never posts an order or accepts the owner's private key. The
caller supplies a secure SDK client backed by the separate session key and an
owner-authenticated read gateway for current grant verification.
"""
from dataclasses import asdict
import time
from eth_abi import decode, encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from polymarket._internal.actions.orders.post import build_post_order_request
from polymarket._internal.actions.orders.types import UnsignedOrder
from polymarket._internal.actions.orders.typed_data import build_order_typed_data, build_order_signature
from app.services.live_order_journal import number

EXCHANGES = {'0xe111180000d2663c0091e4f400237545b87b996b', '0xe2222d279d744050d28e00520010520000310f59'}
SESSION_MAGIC = bytes.fromhex('6492' * 16)


def verify_session_order(signed, *, session_address, wallet, exchange_address):
    """Verify both wrapper layers and recover the authorized session signer."""
    if exchange_address.lower() not in EXCHANGES:
        raise ValueError('Unsupported exchange deployment')
    if (signed.signature_type != 3 or signed.maker.lower() != wallet.lower()
            or signed.signer.lower() != wallet.lower()):
        raise ValueError('Order is not for the authorized Deposit Wallet')
    fields = asdict(signed)
    fields.pop('post_only')
    signature = bytes.fromhex(fields.pop('signature').removeprefix('0x'))
    if not signature.endswith(SESSION_MAGIC):
        raise ValueError('Missing scoped session envelope')
    signer_id, reserved, inner = decode(['bytes32', 'bytes32', 'bytes'], signature[:-32])
    if encode(['bytes32', 'bytes32', 'bytes'], [signer_id, reserved, inner]) != signature[:-32]:
        raise ValueError('Noncanonical session envelope')
    expected_signer = bytes.fromhex(session_address.removeprefix('0x')).rjust(32, b'\x00')
    if signer_id != expected_signer or reserved != bytes(32):
        raise ValueError('Session signer identity mismatch')
    unsigned = UnsignedOrder(**fields, chain_id=137, exchange_address=exchange_address)
    raw_signature = '0x' + inner[:65].hex()
    expected_inner = bytes.fromhex(build_order_signature(unsigned, raw_signature).removeprefix('0x'))
    if inner != expected_inner:
        raise ValueError('Order payload or exchange domain differs from signature')
    typed = build_order_typed_data(unsigned)
    recovered = Account.recover_message(encode_typed_data(full_message=typed), signature=raw_signature)
    if recovered.lower() != session_address.lower():
        raise ValueError('Invalid session signature')
    # Exchange order identity hashes Order, not its Deposit Wallet wrapper.
    standard = {'domain': typed['domain'], 'types': {'Order': typed['types']['Order']},
                'primaryType': 'Order', 'message': typed['message']['contents']}
    encoded = encode_typed_data(full_message=standard)
    return '0x' + keccak(b'\x19' + encoded.version + encoded.header + encoded.body).hex()


class ScopedOrderSigner:
    def __init__(self, sdk_client, owner_gateway, session_gateway, *, wallet, session_address):
        self.client, self.owner_gateway, self.session_gateway = sdk_client, owner_gateway, session_gateway
        self.wallet, self.session_address = wallet.lower(), session_address.lower()

    async def verify_authorization(self):
        if (self.client.wallet_type != 'DEPOSIT_WALLET' or self.client.wallet.lower() != self.wallet
                or self.client.signer.lower() != self.session_address
                or self.session_gateway.credentials.signer_address.lower() != self.session_address
                or self.owner_gateway.credentials.signer_address.lower() == self.session_address):
            raise PermissionError('Separate owner and session identities are required')
        response = await self.owner_gateway._get('/v1/user/session-signers')
        if not isinstance(response, dict) or response.get('wallet', '').lower() != self.wallet:
            raise PermissionError('Session grant wallet mismatch')
        matches = [s for s in response.get('signers', []) if s.get('address', '').lower() == self.session_address]
        if len(matches) != 1:
            raise PermissionError('Session grant absent or ambiguous')
        grant = matches[0]
        if set(grant.get('scopes', [])) != {'CLOB'}:
            raise PermissionError('Authorization must be limited to CLOB trading')
        expires = grant.get('valid_until')
        if isinstance(expires, bool) or not isinstance(expires, int) or expires <= time.time() + 300:
            raise PermissionError('Session authorization expired or near expiry')
        return expires

    async def sign_limit(self, *, token_id, side, quantity, price, exchange_address):
        expiry = await self.verify_authorization()
        if exchange_address.lower() not in EXCHANGES:
            raise ValueError('Unsupported exchange deployment')
        qty, px = number(quantity, positive=True), number(price, positive=True)
        if side not in ('BUY', 'SELL') or px >= 1:
            raise ValueError('Invalid order side or price')
        # Bounded lifetime; SDK fetches current tick/min-size context. It signs
        # only: the journal must commit a reservation before any POST.
        expiration = min(int(time.time()) + 240, expiry - 30)
        signed = await self.client.create_limit_order(token_id=token_id, side=side,
            size=qty, price=px, expiration=expiration)
        raw_shares = number(signed.taker_amount if side == 'BUY' else signed.maker_amount)
        raw_cash = number(signed.maker_amount if side == 'BUY' else signed.taker_amount)
        if (str(signed.token_id) != token_id or signed.side != side or raw_shares != qty * 1000000
                or raw_cash != qty * px * 1000000 or signed.expiration != expiration):
            raise ValueError('Signed amounts differ from the approved intent')
        order_hash = verify_session_order(signed, session_address=self.session_address,
                                         wallet=self.wallet, exchange_address=exchange_address)
        # Catch revocation during market-context reads/signing.
        await self.verify_authorization()
        _, envelope = build_post_order_request(signed, owner_api_key=self.session_gateway.credentials.api_key)
        return {'signed_order_hash': order_hash, 'envelope': envelope, 'authorization_expires_at': expiry}
