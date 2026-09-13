import base64
import hashlib
import hmac
import json
from decimal import Decimal
import httpx
import pytest
from app.services.clob_gateway import (ClobCredentials, ClobGateway, ExchangeUnavailable,
                                      ExchangeAuthenticationError, SubmissionUncertain)


CREDS = ClobCredentials('0x' + '1' * 40, 'fixture-key', base64.b64encode(b'fixture-secret').decode(), 'fixture-pass')


@pytest.mark.asyncio
async def test_cancel_signs_exact_body_and_does_not_claim_a_fill():
    oid = '0x' + 'a' * 64
    def handle(request):
        assert request.method == 'DELETE' and request.url.path == '/order'
        assert request.content == json.dumps({'orderID': oid}, separators=(',', ':')).encode()
        expected = CREDS.headers('DELETE', '/order', request.content.decode(), int(request.headers['POLY_TIMESTAMP']))
        assert request.headers['POLY_SIGNATURE'] == expected['POLY_SIGNATURE']
        return httpx.Response(200, json={'canceled': [oid], 'not_canceled': {}})
    async with httpx.AsyncClient(base_url='https://exchange.test', transport=httpx.MockTransport(handle)) as client:
        assert (await ClobGateway(CREDS, client).cancel_order(oid))['canceled'] == [oid]


@pytest.mark.asyncio
@pytest.mark.parametrize('second', [
    {'data': [], 'next_cursor': 'MA=='},
    {'data': [{'id': 'first'}], 'next_cursor': 'LTE='},
    {'data': []}, []])
async def test_incomplete_repeated_pagination_never_returns_partial_success(second):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={'data': [{'id': 'first'}], 'next_cursor': 'page2'} if len(calls) == 1 else second)
    async with httpx.AsyncClient(base_url='https://exchange.test', transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ExchangeUnavailable):
            await ClobGateway(CREDS, client).open_orders()


@pytest.mark.asyncio
async def test_explicit_terminal_empty_page_is_valid():
    async with httpx.AsyncClient(base_url='https://exchange.test', transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={'data': [], 'next_cursor': 'LTE='}))) as client:
        assert await ClobGateway(CREDS, client).open_orders() == []


@pytest.mark.asyncio
async def test_authenticated_zero_balance_is_not_position_value():
    def handle(request):
        assert request.url.path == '/balance-allowance'
        assert request.url.params['asset_type'] == 'COLLATERAL'
        assert request.headers['POLY_ADDRESS'] == CREDS.signer_address
        ts = request.headers['POLY_TIMESTAMP']
        expected = base64.urlsafe_b64encode(hmac.new(b'fixture-secret', (ts + 'GET/balance-allowance').encode(), hashlib.sha256).digest()).decode()
        assert request.headers['POLY_SIGNATURE'] == expected
        return httpx.Response(200, json={'balance': '0', 'allowances': {}, 'currentValue': 10000})
    async with httpx.AsyncClient(base_url='https://exchange.test', transport=httpx.MockTransport(handle)) as client:
        evidence = await ClobGateway(CREDS, client).collateral_balance(0)
        assert evidence['balance'] == Decimal(0)


@pytest.mark.asyncio
@pytest.mark.parametrize('status,data,error', [(401, {}, ExchangeAuthenticationError),
    (403, {}, ExchangeAuthenticationError), (503, {}, ExchangeUnavailable),
    (200, {'currentValue': 10000}, ExchangeUnavailable),
    (200, {'balance': 'NaN', 'allowances': {}}, ExchangeUnavailable)])
async def test_invalid_or_unauthorized_balance_is_unavailable(status, data, error):
    async with httpx.AsyncClient(base_url='https://exchange.test', transport=httpx.MockTransport(
            lambda request: httpx.Response(status, json=data))) as client:
        with pytest.raises(error):
            await ClobGateway(CREDS, client).collateral_balance(0)


@pytest.mark.asyncio
async def test_submission_is_authorized_explicitly_and_timeout_is_not_retried():
    calls = []
    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout('fixture timeout', request=request)
    async with httpx.AsyncClient(base_url='https://exchange.test', transport=httpx.MockTransport(handle)) as client:
        gateway = ClobGateway(CREDS, client)
        envelope = {'order': {'signature': 'fixture-signature'}}
        with pytest.raises(PermissionError):
            await gateway.submit_signed_order(envelope)
        assert calls == []
        with pytest.raises(SubmissionUncertain):
            await gateway.submit_signed_order(envelope, submission_authorized=True)
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_signed_body_matches_sent_bytes_and_ack_is_not_a_fill():
    def handle(request):
        expected_body = b'{"order":{"signature":"fixture-signature"},"orderType":"GTC"}'
        assert request.content == expected_body
        message = request.headers['POLY_TIMESTAMP'].encode() + b'POST/order' + expected_body
        expected = base64.urlsafe_b64encode(hmac.new(b'fixture-secret', message, hashlib.sha256).digest()).decode()
        assert request.headers['POLY_SIGNATURE'] == expected
        return httpx.Response(200, json={'success': True, 'orderID': '0x' + 'a' * 64, 'status': 'live'})
    async with httpx.AsyncClient(base_url='https://exchange.test', transport=httpx.MockTransport(handle)) as client:
        result = await ClobGateway(CREDS, client).submit_signed_order(
            {'order': {'signature': 'fixture-signature'}, 'orderType': 'GTC'}, submission_authorized=True)
        assert result['status'] == 'live'
        assert 'filled_shares' not in result
