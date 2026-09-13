"""Deterministic submission risk checks. All limits/evidence are explicit inputs.

No default buying power, fee schedule, wallet ranking or market price. This gate
must be re-evaluated at submission with current account and venue observations.
"""
from dataclasses import dataclass
from decimal import Decimal
from app.services.live_order_journal import number


class RiskRejected(ValueError):
    pass


@dataclass(frozen=True)
class RiskLimits:
    max_order_cash: Decimal
    max_total_exposure: Decimal
    max_token_exposure: Decimal
    max_daily_loss: Decimal
    max_open_orders: int
    max_slippage_bps: Decimal
    max_quote_age_ms: int
    max_source_age_ms: int

    def validate(self):
        for value in (self.max_order_cash, self.max_total_exposure, self.max_token_exposure, self.max_daily_loss):
            number(value, positive=True)
        if not 0 <= number(self.max_slippage_bps) <= 10000:
            raise RiskRejected('Invalid slippage limit')
        for value in (self.max_open_orders, self.max_quote_age_ms, self.max_source_age_ms):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise RiskRejected('Invalid risk limits')


def check_live_order(*, limits, side, token_id, quantity, limit_price, fee_budget,
                     source_price, source_timestamp_ms, now_ms, book, accepting_orders,
                     available_cash, available_shares, total_exposure, token_exposure,
                     daily_loss, open_order_count):
    limits.validate()
    qty, price, fee = number(quantity, positive=True), number(limit_price, positive=True), number(fee_budget)
    reference = number(source_price, positive=True)
    if side not in ('BUY', 'SELL') or price >= 1 or reference >= 1:
        raise RiskRejected('Invalid order side or price')
    if accepting_orders is not True or book.get('asset_id') != token_id:
        raise RiskRejected('Market closed or token identity mismatch')
    for timestamp, maximum in ((book.get('timestamp'), limits.max_quote_age_ms), (source_timestamp_ms, limits.max_source_age_ms)):
        # Venue timestamps are Unix milliseconds. Do not substitute receipt time.
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, str)) or not str(timestamp).isdigit():
            raise RiskRejected('Missing source or quote timestamp')
        if not 0 <= now_ms - int(timestamp) <= maximum:
            raise RiskRejected('Stale or future-dated source/quote')
    tick, minimum = number(book.get('tick_size', -1), positive=True), number(book.get('min_order_size', -1), positive=True)
    if tick not in map(Decimal, ('0.1', '0.01', '0.005', '0.0025', '0.001', '0.0001')):
        raise RiskRejected('Unsupported current tick size')
    if price % tick or qty < minimum or qty * 100 != (qty * 100).to_integral_value():
        raise RiskRejected('Price tick or share precision/minimum violated')
    adverse = (price - reference) / reference if side == 'BUY' else (reference - price) / reference
    if adverse * 10000 > number(limits.max_slippage_bps):
        raise RiskRejected('Source-price slippage limit exceeded')
    if isinstance(open_order_count, bool) or not isinstance(open_order_count, int) or open_order_count < 0:
        raise RiskRejected('Open-order count unavailable')
    if open_order_count >= limits.max_open_orders:
        raise RiskRejected('Open-order limit reached')
    cost = qty * price + fee
    if cost > limits.max_order_cash:
        raise RiskRejected('Per-order cash limit exceeded')
    if side == 'BUY':
        if number(daily_loss) >= limits.max_daily_loss:
            raise RiskRejected('Daily loss limit reached')
        if cost > number(available_cash):
            raise RiskRejected('Insufficient cash including fees')
        if number(total_exposure) + cost > limits.max_total_exposure or number(token_exposure) + cost > limits.max_token_exposure:
            raise RiskRejected('Exposure limit exceeded')
    elif qty > number(available_shares):
        raise RiskRejected('Insufficient unreserved shares')
    # Even risk-reducing exits require a real book and bounded execution price.
    rows = book.get('asks' if side == 'BUY' else 'bids')
    if not isinstance(rows, list):
        raise RiskRejected('Order book unavailable')
    depth = Decimal(0)
    for row in rows:
        level_price, size = number(row.get('price', -1), positive=True), number(row.get('size', -1))
        if level_price >= 1:
            raise RiskRejected('Invalid order-book level')
        if (level_price <= price if side == 'BUY' else level_price >= price):
            depth += size
    if depth < qty:
        raise RiskRejected('Insufficient displayed liquidity within limit')
    return {'cash_at_risk': cost, 'quantity': qty, 'limit_price': price}
