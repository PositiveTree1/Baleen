"""Current market/book evidence and the contract's maximum fee bound."""
from decimal import Decimal
import time
from eth_utils import keccak
from app.services.live_order_journal import number
from app.services.live_risk import RiskRejected
from app.services.settlement_receipts import hex_number

STANDARD = '0xe111180000d2663c0091e4f400237545b87b996b'
NEG_RISK = '0xe2222d279d744050d28e00520010520000310f59'


class LiveMarketEvidence:
    def __init__(self, http, rpc):
        self.http, self.rpc = http, rpc

    async def source(self, source):
        return await self.rpc.source(source)

    async def _get(self, path, params=None):
        response = await self.http.get(path, params=params)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RiskRejected('Market evidence unavailable')
        return result

    async def market(self, condition_id, token_id):
        if not condition_id or not token_id:
            raise RiskRejected('Source market identity unresolved')
        market = await self._get('/markets/' + condition_id)
        if (market.get('condition_id') != condition_id or not isinstance(market.get('neg_risk'), bool)
                or not any(str(t.get('token_id')) == token_id for t in market.get('tokens', []))):
            raise RiskRejected('Market/token identity mismatch')
        exchange = NEG_RISK if market['neg_risk'] else STANDARD
        if hex_number(await self.rpc.rpc('eth_chainId', [])) != 137:
            raise RiskRejected('Fee-bound chain mismatch')
        selector = '0x' + keccak(text='getMaxFeeRate()')[:4].hex()
        maximum = hex_number(await self.rpc.rpc('eth_call', [{'to':exchange,'data':selector}, 'latest']))
        # Fees.sol treats zero as unlimited, not as a fee-free market.
        if not 0 < maximum < 10000:
            raise RiskRejected('Contract fee bound unavailable or unlimited')
        return {'book': await self._get('/book', {'token_id':token_id}), 'exchange':exchange,
                'accepting_orders':market.get('accepting_orders'), 'fee_cap_bps':maximum}

    async def mark(self, token_id, max_age_ms):
        book = await self._get('/book', {'token_id':token_id})
        ts = book.get('timestamp')
        if (book.get('asset_id') != token_id or not str(ts).isdigit()
                or not 0 <= int(time.time()*1000)-int(ts) <= max_age_ms):
            raise RiskRejected('Position mark stale or unavailable')
        prices = [number(r['price']) for r in book.get('bids', []) if number(r['size']) > 0]
        if not prices or any(p > 1 for p in prices):
            raise RiskRejected('Executable position bid unavailable')
        return max(prices)
