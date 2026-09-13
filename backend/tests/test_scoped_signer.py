"""Offline cryptographic verification using generated session keys, never real funds."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
import time
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from polymarket._internal.actions.orders.types import UnsignedOrder
from polymarket._internal.actions.orders.typed_data import build_order_typed_data, build_order_signature
from polymarket._internal.actions.orders.orders import create_signed_order
from polymarket._internal.wallet import wrap_deposit_wallet_session_signer_signature
from app.services.scoped_signer import verify_session_order, ScopedOrderSigner

EXCHANGE = '0xE111180000d2663C0091e4f400237545B87B996B'
WALLET = '0x' + '2' * 40
ZERO = '0x' + '0' * 64


def signed_fixture():
    account = Account.create()
    order = UnsignedOrder(chain_id=137, exchange_address=EXCHANGE, builder=ZERO, expiration=int(time.time()) + 240,
        maker=WALLET, maker_amount=50000000, metadata=ZERO, order_type='GTD', salt=123456789,
        side='BUY', signature_type=3, signer=WALLET, taker_amount=100000000, timestamp=int(time.time() * 1000), token_id='111')
    typed = build_order_typed_data(order)
    inner = account.sign_message(encode_typed_data(full_message=typed))
    wrapped = build_order_signature(order, '0x' + inner.signature.hex())
    signature = wrap_deposit_wallet_session_signer_signature(account.address, wrapped)
    return account, create_signed_order(order, signature, post_only=False), typed


def test_session_order_has_verified_exchange_identity():
    account, signed, typed = signed_fixture()
    actual = verify_session_order(signed, session_address=account.address, wallet=WALLET, exchange_address=EXCHANGE)
    domain = typed['domain']
    # Compute plain Order identity independently of the wrapper verifier.
    plain = encode_typed_data(domain, {'Order': typed['types']['Order']}, typed['message']['contents'])
    assert actual == '0x' + keccak(b'\x19\x01' + plain.header + plain.body).hex()


@pytest.mark.parametrize('change', [{'token_id': '112'}, {'maker_amount': 50000001},
    {'side': 'SELL'}, {'signature_type': 0}, {'maker': '0x' + '3' * 40}])
def test_tampered_signed_order_rejected(change):
    account, signed, _ = signed_fixture()
    with pytest.raises(ValueError):
        verify_session_order(replace(signed, **change), session_address=account.address, wallet=WALLET, exchange_address=EXCHANGE)


def test_wrong_session_or_exchange_rejected():
    account, signed, _ = signed_fixture()
    for session, exchange in [('0x' + '4' * 40, EXCHANGE),
            (account.address, '0xe2222d279d744050d28e00520010520000310f59')]:
        with pytest.raises(ValueError):
            verify_session_order(signed, session_address=session, wallet=WALLET, exchange_address=exchange)


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['revoked', 'expired', 'broad_scope', 'wrong_wallet'])
async def test_invalid_session_grant_never_signs(fault):
    account, _, _ = signed_fixture()
    client = SimpleNamespace(wallet_type='DEPOSIT_WALLET', wallet=WALLET, signer=account.address, create_limit_order=AsyncMock())
    owner = AsyncMock()
    owner.credentials = SimpleNamespace(signer_address='0x' + '5' * 40)
    session = SimpleNamespace(credentials=SimpleNamespace(signer_address=account.address, api_key='fixture'))
    grant = {'address': account.address, 'scopes': ['CLOB'], 'valid_until': int(time.time()) + 600}
    owner._get.return_value = {'wallet': WALLET, 'signers': [grant]}
    if fault == 'revoked': owner._get.return_value['signers'] = []
    if fault == 'expired': grant['valid_until'] = 1
    if fault == 'broad_scope': grant['scopes'].append('COMBOSRFQ')
    if fault == 'wrong_wallet': owner._get.return_value['wallet'] = '0x' + '9' * 40
    with pytest.raises(PermissionError):
        await ScopedOrderSigner(client, owner, session, wallet=WALLET, session_address=account.address).sign_limit(
            token_id='111', side='BUY', quantity=100, price='.5', exchange_address=EXCHANGE)
    client.create_limit_order.assert_not_awaited()
