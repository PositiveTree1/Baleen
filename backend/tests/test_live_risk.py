from dataclasses import replace
from decimal import Decimal as D
import pytest
from app.services.live_risk import RiskLimits, RiskRejected, check_live_order


def inputs():
    return dict(limits=RiskLimits(D(100), D(500), D(200), D(50), 5, D(100), 1000, 10000),
        side='BUY', token_id='111', quantity='10', limit_price='.5', fee_budget='.1', source_price='.5',
        source_timestamp_ms=95000, now_ms=100000,
        book={'asset_id': '111', 'timestamp': '99900', 'tick_size': '.01', 'min_order_size': '5',
              'asks': [{'price': '.5', 'size': '20'}], 'bids': [{'price': '.5', 'size': '20'}]},
        accepting_orders=True, available_cash='100', available_shares='20', total_exposure='0',
        token_exposure='0', daily_loss='0', open_order_count=0)


@pytest.mark.parametrize('field,value', [('accepting_orders', False), ('available_cash', '5'),
    ('daily_loss', '50'), ('total_exposure', '499'), ('token_exposure', '199'),
    ('open_order_count', 5), ('quantity', '4'), ('quantity', '10.001'),
    ('limit_price', '.501'), ('source_price', '.4'), ('source_timestamp_ms', 100001),
    ('source_timestamp_ms', 1), ('fee_budget', 'NaN')])
def test_entry_risk_constraints_reject(field, value):
    args = inputs()
    args[field] = value
    with pytest.raises(ValueError): check_live_order(**args)


@pytest.mark.parametrize('field,value', [('timestamp', '1'), ('timestamp', None), ('asset_id', 'other'),
    ('asks', []), ('tick_size', '0'), ('min_order_size', '11')])
def test_missing_or_stale_venue_evidence_rejects(field, value):
    args = inputs()
    args['book'][field] = value
    with pytest.raises(ValueError): check_live_order(**args)


def test_valid_zero_loss_and_exit_after_loss_limit():
    args = inputs()
    assert check_live_order(**args)['cash_at_risk'] == D('5.1')
    args.update(side='SELL', daily_loss='100', total_exposure='999', token_exposure='999', available_cash='0')
    assert check_live_order(**args)['quantity'] == 10
    args['available_shares'] = '9'
    with pytest.raises(RiskRejected): check_live_order(**args)
