import os
from pathlib import Path

# Ensure tests run against an isolated test SQLite DB
test_db_path = Path(__file__).resolve().parent.parent / "test_baleen.db"
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{test_db_path.as_posix()}"

import pytest

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    if test_db_path.exists():
        try:
            os.remove(test_db_path)
        except Exception:
            pass

@pytest.fixture
def make_wallet_stats():
    def _make(pnl=100000.0, trades_per_day=5.0, outlier_pct=0.1, win_rate=90.0, max_drawdown=5.0, is_boundary_arb=False):
        return {
            'all_time_pnl_usd': pnl,
            'avg_trades_per_day': trades_per_day,
            'outlier_concentration_pct': outlier_pct,
            'win_rate_pct': win_rate,
            'max_drawdown_pct': max_drawdown,
            'is_boundary_arb': is_boundary_arb,
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
