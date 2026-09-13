"""Presentation values from recorded fills and fresh observed marks only."""
import math
from app.services.mark_to_market import get_observed_price


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        return None
    return float(value)


def execution_valuation(log):
    fill = finite(log.user_fill_price)
    # A whale price is not evidence of a follower fill.
    if fill is not None and not 0 <= fill <= 1:
        fill = None
    notional, fee = finite(log.notional_usd), finite(log.fee_usd)
    observed = get_observed_price(log.market_condition_id or '', log.resolution_outcome or '', log.token_id or '')
    current = observed['price'] if observed else None
    gross = net = None
    if log.status in ('CLOSED', 'RESOLVED'):
        net = finite(log.realized_pnl_usd)
        # Entry fee alone does not prove total round-trip fees or gross profit.
    elif log.status == 'FILLED' and fill is not None and fill > 0 and current is not None and notional is not None:
        direction = 1 if log.side == 'BUY' else -1
        gross = round(direction * notional * (current - fill) / fill, 2)
        if fee is not None:
            net = round(gross - fee, 2)
    return {'fillPrice': fill, 'currentPrice': current, 'feeUsd': fee, 'pnl': net, 'grossPnl': gross,
            'pnlPct': round(net / notional * 100, 2) if net is not None and notional is not None and notional > 0 else None,
            'markStatus': 'observed' if observed else 'unavailable',
            'markObservedAt': observed['observed_at'] if observed else None}
