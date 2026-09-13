"""Authenticated CLOB transport. No public-data substitute for private balances.

Protocol reference: https://docs.polymarket.com/getting-started/api
Reviewed 2026-09-10. Order submission must be driven by a durable order journal,
not directly from an HTTP user request or a simulated paper fill.
"""
import base64
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
import httpx


class ExchangeUnavailable(RuntimeError):
    pass


class ExchangeAuthenticationError(RuntimeError):
    pass


class SubmissionUncertain(RuntimeError):
    """The exchange may have accepted the request. Reconcile; never blindly retry."""


@dataclass(frozen=True)
class ClobCredentials:
    signer_address: str
    api_key: str = field(repr=False)
    secret: str = field(repr=False)
    passphrase: str = field(repr=False)

    def headers(self, method: str, path: str, body: str = '', timestamp: int | None = None):
        if not re.fullmatch(r'0x[0-9a-fA-F]{40}', self.signer_address):
            raise ValueError('A verified signer address is required')
        if not self.api_key or not self.secret or not self.passphrase:
            raise ValueError('Complete CLOB credentials are required')
        try:
            key = base64.b64decode(self.secret, altchars=b'-_', validate=True)
        except Exception as exc:
            raise ValueError('Invalid encoded CLOB secret') from exc
        if not key:
            raise ValueError('Empty CLOB secret')
        ts = str(int(time.time()) if timestamp is None else timestamp)
        message = ts + method.upper() + path + body
        signature = base64.urlsafe_b64encode(hmac.new(key, message.encode(), hashlib.sha256).digest()).decode()
        return {'POLY_ADDRESS': self.signer_address.lower(), 'POLY_API_KEY': self.api_key,
                'POLY_PASSPHRASE': self.passphrase, 'POLY_TIMESTAMP': ts,
                'POLY_SIGNATURE': signature}


class ClobGateway:
    def __init__(self, credentials: ClobCredentials, client: httpx.AsyncClient):
        self.credentials = credentials
        self.client = client

    async def _get(self, path, params=None):
        try:
            response = await self.client.get(path, params=params, headers=self.credentials.headers('GET', path))
        except httpx.HTTPError as exc:
            raise ExchangeUnavailable('Authenticated exchange request failed') from exc
        if response.status_code in (401, 403):
            raise ExchangeAuthenticationError('Exchange rejected the credentials or account access')
        if response.status_code != 200:
            raise ExchangeUnavailable(f'Exchange returned HTTP {response.status_code}')
        try:
            return response.json()
        except ValueError as exc:
            raise ExchangeUnavailable('Exchange returned malformed JSON') from exc

    async def collateral_balance(self, signature_type: int):
        if signature_type not in (0, 1, 2, 3):
            raise ValueError('Unsupported wallet signature type')
        result = await self._get('/balance-allowance', {'asset_type': 'COLLATERAL', 'signature_type': signature_type})
        raw = result.get('balance') if isinstance(result, dict) else None
        if not isinstance(raw, (str, int)) or isinstance(raw, bool) or not re.fullmatch(r'[0-9]+', str(raw)):
            raise ExchangeUnavailable('Missing or invalid collateral balance')
        allowances = result.get('allowances')
        if not isinstance(allowances, dict):
            raise ExchangeUnavailable('Missing collateral allowance evidence')
        return {'balance': Decimal(str(raw)) / Decimal(1000000), 'allowances': allowances,
                'source': 'authenticated_clob', 'signature_type': signature_type}

    async def get_order(self, order_id: str):
        if not re.fullmatch(r'0x[0-9a-fA-F]{64}', order_id):
            raise ValueError('Expected exchange order hash')
        result = await self._get('/data/order/' + order_id)
        if not isinstance(result, dict) or str(result.get('id', '')).lower() != order_id.lower():
            raise ExchangeUnavailable('Order identity mismatch')
        return result

    async def _pages(self, path, params=None, *, max_pages=100):
        """Require an explicit terminal cursor; a bare array is not coverage proof."""
        rows, identities, cursors = [], set(), set()
        cursor = 'MA=='
        for _ in range(max_pages):
            if cursor in cursors:
                raise ExchangeUnavailable('Exchange pagination repeated a cursor')
            cursors.add(cursor)
            page = await self._get(path, {**(params or {}), 'next_cursor': cursor})
            if not isinstance(page, dict) or not isinstance(page.get('data'), list):
                raise ExchangeUnavailable('Exchange pagination completeness unavailable')
            for row in page['data']:
                identity = row.get('id') if isinstance(row, dict) else None
                if not isinstance(identity, str) or not identity or identity in identities:
                    raise ExchangeUnavailable('Invalid or repeated exchange record')
                identities.add(identity)
                rows.append(row)
            cursor = page.get('next_cursor')
            if cursor == 'LTE=':
                return rows
            if not isinstance(cursor, str) or not cursor:
                raise ExchangeUnavailable('Exchange pagination has no terminal evidence')
        raise ExchangeUnavailable('Exchange pagination exceeded coverage limit')

    async def open_orders(self):
        return await self._pages('/data/orders')

    async def trades_for_id(self, trade_id):
        if not isinstance(trade_id, str) or not trade_id or len(trade_id) > 255:
            raise ValueError('Invalid trade identity')
        rows = await self._pages('/data/trades', {'id': trade_id})
        if len(rows) != 1 or rows[0]['id'] != trade_id:
            raise ExchangeUnavailable('Associated trade missing or identity mismatch')
        return rows[0]

    async def token_balance(self, token_id, signature_type):
        if not re.fullmatch(r'[0-9]+', token_id) or signature_type not in (0, 1, 2, 3):
            raise ValueError('Invalid token/wallet type')
        result = await self._get('/balance-allowance', {
            'asset_type': 'CONDITIONAL', 'token_id': token_id, 'signature_type': signature_type})
        raw = result.get('balance') if isinstance(result, dict) else None
        if not isinstance(raw, str) or not re.fullmatch(r'[0-9]+', raw):
            raise ExchangeUnavailable('Token balance unavailable')
        return Decimal(raw) / Decimal(1000000)

    async def submit_signed_order(self, envelope: dict[str, Any], *, submission_authorized: bool = False):
        if not submission_authorized:
            raise PermissionError('Submission requires a reserved, authorized order intent')
        order = envelope.get('order')
        if not isinstance(order, dict) or not order.get('signature'):
            raise ValueError('A signed exchange order is required')
        # Sign exactly the bytes sent; httpx json= may choose another encoding.
        body = json.dumps(envelope, separators=(',', ':'), allow_nan=False)
        try:
            response = await self.client.post('/order', content=body,
                headers={**self.credentials.headers('POST', '/order', body), 'Content-Type': 'application/json'})
        except httpx.HTTPError as exc:
            raise SubmissionUncertain('Order outcome unknown; reconcile the signed order hash') from exc
        if response.status_code >= 500:
            raise SubmissionUncertain('Exchange outcome unknown; do not create another order')
        if response.status_code in (401, 403):
            raise ExchangeAuthenticationError('Exchange rejected order credentials')
        try:
            result = response.json()
        except ValueError as exc:
            raise SubmissionUncertain('Malformed order acknowledgement; reconcile') from exc
        if response.status_code != 200 or not isinstance(result, dict) or result.get('success') is not True:
            raise ExchangeUnavailable('Exchange did not accept the order')
        if not result.get('orderID'):
            raise SubmissionUncertain('Acknowledgement has no order identity')
        # Acceptance is not a fill. The reconciliation worker owns fill records.
        return result

    async def cancel_order(self, order_id: str):
        """Request cancellation of one journal-owned hash; never infer a final fill state.

        Protocol: https://docs.polymarket.com/api-reference/trade/cancel-single-order
        """
        if not re.fullmatch(r'0x[0-9a-fA-F]{64}', order_id):
            raise ValueError('Expected exchange order hash')
        body = json.dumps({'orderID': order_id}, separators=(',', ':'))
        try:
            response = await self.client.request('DELETE', '/order', content=body,
                headers={**self.credentials.headers('DELETE', '/order', body), 'Content-Type': 'application/json'})
        except httpx.HTTPError as exc:
            raise ExchangeUnavailable('Cancellation outcome unknown; reconcile') from exc
        if response.status_code in (401, 403):
            raise ExchangeAuthenticationError('Exchange rejected cancellation credentials')
        if response.status_code != 200:
            raise ExchangeUnavailable('Cancellation not acknowledged; reconcile')
        try:
            result = response.json()
        except ValueError as exc:
            raise ExchangeUnavailable('Malformed cancellation response') from exc
        if not isinstance(result, dict) or not isinstance(result.get('canceled'), list) or not isinstance(result.get('not_canceled'), dict):
            raise ExchangeUnavailable('Cancellation result unavailable')
        return result
