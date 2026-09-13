import time
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models import User, Wallet, ExecutionLog
from app.services.execution_valuation import execution_valuation
from app.services.mark_to_market import _live_price_cache, get_observed_price


def lot(**overrides):
    fields = dict(user_fill_price=.5, whale_entry_price=.6, fee_usd=0, notional_usd=10,
        market_condition_id='truth-test', resolution_outcome='Yes', token_id='truth-token',
        status='FILLED', side='BUY', realized_pnl_usd=None)
    return SimpleNamespace(**(fields | overrides))


def test_unknown_mark_and_missing_fill_do_not_invent_flat_pnl():
    _live_price_cache.pop('truth-token', None)
    _live_price_cache.pop('truth-test:yes', None)
    value = execution_valuation(lot())
    assert value['currentPrice'] is None and value['pnl'] is None
    assert execution_valuation(lot(user_fill_price=None))['fillPrice'] is None


def test_zero_mark_is_total_price_loss_and_zero_fee_is_preserved():
    _live_price_cache['truth-token'] = {'price': 0.0, 'ts': time.time()}
    try:
        result = execution_valuation(lot())
        assert result['currentPrice'] == 0 and result['pnl'] == -10 and result['feeUsd'] == 0
    finally:
        _live_price_cache.pop('truth-token', None)


@pytest.mark.parametrize('price,age', [(float('nan'), 0), (.5, 61), (.5, -100), (1.1, 0)])
def test_invalid_stale_and_future_observation_rejected(price, age):
    _live_price_cache['truth-token'] = {'price': price, 'ts': time.time() - age}
    try:
        assert get_observed_price(asset='truth-token') is None
    finally:
        _live_price_cache.pop('truth-token', None)


@pytest.mark.asyncio
async def test_public_wallet_detail_never_exposes_private_copies_or_invents_history(monkeypatch):
    from app.api.wallets import get_wallet
    import app.api.wallets as api
    monkeypatch.setattr(api, 'generate_summary', AsyncMock(side_effect=RuntimeError('fixture outage')))
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    uid = uuid.uuid4()
    address = '0x' + '7' * 40
    async with sessions() as db:
        db.add(User(id=uid, email='truth-fixture@example.invalid'))
        db.add(Wallet(address=address, cached_daily_pnl='[{"date":"2026-01-01","pnl":0}]'))
        await db.flush()
        db.add(ExecutionLog(user_id=uid, source_wallet_address=address, side='BUY',
            status='FILLED', is_sandbox=True, notional_usd=100, market_question='PRIVATE FIXTURE'))
        await db.commit()
        response = await get_wallet(address, db=db)
        assert 'PRIVATE FIXTURE' not in str(response)
        assert response['score_history'] == []
        assert response.get('ai_summary') is None
    await engine.dispose()
