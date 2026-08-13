import pytest

@pytest.fixture
def make_wallet_stats():
    def _make(pnl=100000.0, trades_per_day=5.0, outlier_pct=0.1, win_rate=90.0, max_drawdown=5.0):
        return {
            'all_time_pnl_usd': pnl,
            'avg_trades_per_day': trades_per_day,
            'outlier_concentration_pct': outlier_pct,
            'win_rate_pct': win_rate,
            'max_drawdown_pct': max_drawdown
        }
    return _make

@pytest.fixture
def make_user():
    def _make(balance=10000.0, risk_profile='balanced'):
        return {
            'sandbox_balance_usd': balance,
            'risk_profile': risk_profile
        }
    return _make

@pytest.fixture
def make_whale_trade():
    def _make(trade_value=50000.0, portfolio_value=500000.0):
        return {
            'trade_value': trade_value,
            'portfolio_value': portfolio_value
        }
    return _make
