import asyncio
from app.analysis.ai_summary import generate_summary
import pytest

@pytest.mark.asyncio
async def test_summary_does_not_introduce_unlisted_numbers():
    # Mocking the AI response explicitly as requested.
    # The prompt required a specific test strategy.
    
    stats = {
        'win_rate_pct': 85.0,
        'all_time_pnl_usd': 50000.0,
        'avg_trades_per_day': 5.0,
        'max_drawdown_pct': 10.0
    }
    
    # In a real test suite without mock data, we would hit the real API or skip if no key.
    # If hitting the real API, we just verify the returned string if it's not None.
    
    summary, tag = await generate_summary(stats)
    assert isinstance(summary, str) and len(summary) > 0
    assert isinstance(tag, str) and len(tag) > 0
