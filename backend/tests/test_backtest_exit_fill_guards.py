import math

import pytest

from app.backtesting.config import BacktestConfig
from app.backtesting.models import ExecutionFill, TradeSignal
from app.backtesting.portfolio import SimulatedPortfolio


def _signal(side="BUY"):
    return TradeSignal(
        timestamp=100,
        whale_address="0xwhale",
        market_id="market",
        condition_id="condition",
        token_id="token",
        side=side,
        whale_price=0.50,
        whale_size_usd=50.0,
        whale_shares=100.0,
    )


def _fill(signal, *, status="FILLED", price=0.50, size=50.0, shares=100.0, fee=0.0):
    return ExecutionFill(
        order_id="test",
        signal=signal,
        intended_size_usd=50.0,
        fill_price=price,
        filled_size_usd=size,
        filled_shares=shares,
        slippage_bps=0.0,
        fee_usd=fee,
        latency_ms=0.0,
        status=status,
        executed_at=200.0,
    )


def _portfolio_with_position():
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=1000, enable_fees=False))
    portfolio.open_position(_fill(_signal(), size=50.0, shares=100.0))
    return portfolio


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "REJECTED_SLIPPAGE"},
        {"size": 0.0, "shares": 0.0},
        {"size": -1.0, "shares": -1.0},
        {"size": math.nan, "shares": math.nan, "price": math.nan},
        {"size": math.inf, "shares": math.inf, "price": math.inf},
    ],
)
def test_invalid_sell_fill_preserves_position_and_cash(changes):
    portfolio = _portfolio_with_position()
    result = portfolio.close_position_on_whale_sell(
        _signal("SELL"), _fill(_signal("SELL"), **changes)
    )

    assert result is None
    assert portfolio.cash == pytest.approx(950.0)
    assert len(portfolio.open_positions) == 1
    assert next(iter(portfolio.open_positions.values())).shares == pytest.approx(100.0)


def test_valid_sell_fill_caps_overfill_to_position():
    portfolio = _portfolio_with_position()
    result = portfolio.close_position_on_whale_sell(
        _signal("SELL"), _fill(_signal("SELL"), size=100.0, shares=1000.0)
    )

    assert result is not None
    assert result.shares == pytest.approx(100.0)
    assert portfolio.cash == pytest.approx(1000.0)
    assert not portfolio.open_positions
