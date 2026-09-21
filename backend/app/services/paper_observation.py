"""A complete taker leg estimated from observed depth, never an actual fill."""
import json
from decimal import Decimal, ROUND_HALF_UP
from app.sizing.proportional import decimal


def book_quote(book, market, *, token, condition, side, quantity, now_ms):
    if not isinstance(book, dict) or str(book.get('asset_id')) != token or book.get('market') != condition:
        raise ValueError('Book identity unavailable or mismatched')
    if not 0 <= now_ms-int(book['timestamp']) <= 30000:
        raise ValueError('Book is stale or future-dated')
    if not isinstance(market, dict) or market.get('conditionId', '').lower() != condition.lower():
        raise ValueError('Market identity unavailable')
    tokens = market.get('clobTokenIds', [])
    if isinstance(tokens, str): tokens = json.loads(tokens)
    if token not in tokens or market.get('acceptingOrders') is not True or market.get('closed') is not False:
        raise ValueError('Market not accepting orders or token mismatch')
    minimum, tick = decimal(book['min_order_size']), decimal(book['tick_size'])
    if minimum <= 0 or tick <= 0 or quantity < minimum:
        raise ValueError('Proportional quantity below venue minimum or invalid tick')
    enabled = market.get('feesEnabled')
    if enabled is False:
        rate = Decimal(0)
    elif enabled is True:
        schedule = market['feeSchedule']
        if decimal(schedule['exponent']) != 1 or schedule['takerOnly'] is not True:
            raise ValueError('Unsupported fee schedule')
        rate = decimal(schedule['rate'])
        if not 0 <= rate <= 1: raise ValueError('Invalid fee rate')
    else:
        raise ValueError('Fee schedule unavailable')
    if side not in ('BUY', 'SELL'): raise ValueError('Invalid side')
    levels = [(decimal(x['price']), decimal(x['size'])) for x in book['asks' if side == 'BUY' else 'bids']]
    if any(not 0 < p < 1 or q <= 0 or p % tick != 0 for p, q in levels):
        raise ValueError('Invalid book level')
    if len({p for p, _ in levels}) != len(levels): raise ValueError('Repeated book price level')
    remaining, cash, fees = quantity, Decimal(0), Decimal(0)
    consumed = []
    for price, size in sorted(levels, reverse=side == 'SELL'):
        take = min(remaining, size)
        cash += take*price
        fees += take*rate*price*(1-price)
        consumed.append({'price': str(price), 'quantity': str(take)})
        remaining -= take
        if not remaining: break
    if remaining: raise ValueError('Insufficient depth for complete proportional leg')
    # Gamma documents its minimum in USDC; retain both distinct constraints.
    minimum_cash = decimal(market['orderMinSize'])
    if minimum_cash <= 0 or cash < minimum_cash:
        raise ValueError('Proportional order below market notional minimum')
    return {'timestamp': str(Decimal(now_ms)/1000), 'token_id': token, 'side': side,
            'fill_price': str(cash/quantity), 'min_order_size': str(minimum),
            'available_quantity': str(quantity), 'fee_usd': str(fees.quantize(Decimal('.00001'), rounding=ROUND_HALF_UP)),
            'consumed_levels': consumed, 'book': book, 'market': market,
            'estimate': 'observed_depth_taker_estimate_not_exchange_fill'}
