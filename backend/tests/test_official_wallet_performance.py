import time
from unittest.mock import AsyncMock
import pytest
from app.discovery.pnl_history import normalize_pnl_series, verified_history
from app.discovery.polymarket_client import PolymarketClient, ProviderCoverageError
from app.discovery.scanner import calculate_authentic_wallet_stats
from app.scoring.quality import qualify_wallet, quality_score


def history():
    now = int(time.time())
    return normalize_pnl_series([{'t': now-(90-i)*86400, 'p': 1000+i*10} for i in range(91)])


def test_exact_curve_values_zero_negative_baseline_and_order():
    result = normalize_pnl_series([{'t': 1700086400, 'p': 0}, {'t': 1700000000, 'p': 100},
                                   {'t': 1700172800, 'p': -20}])
    assert [p['cumulative_pnl'] for p in result] == [100, 0, -20]
    assert [p['daily_pnl'] for p in result] == [None, -100, -20]
    assert verified_history(result)
    assert not verified_history([{'date': '2026-01-01', 'cumulative_pnl': 999}])


@pytest.mark.parametrize('rows', [None, {}, [{'t': 1, 'p': float('nan')}],
                                    [{'t': 1, 'p': 2}, {'t': 1, 'p': 3}]])
def test_invalid_series_is_unavailable(rows):
    with pytest.raises(ValueError):
        normalize_pnl_series(rows)


def test_zero_realized_pnl_does_not_fall_back_to_floating_profit():
    stats = calculate_authentic_wallet_stats('a', [], [], profile={'pnl': 0}, closed_positions=[
        {'asset': 'a', 'realizedPnl': 0, 'cashPnl': 100}])
    assert stats['win_rate_pct'] == 0
    assert stats['all_time_pnl_usd'] == 0
    assert stats['daily_pnl_history'] == []


def test_open_positions_never_count_as_completed_wins():
    stats = calculate_authentic_wallet_stats('a', [{'asset': 'x', 'size': 100, 'cashPnl': 200,
        'realizedPnl': 20, 'avgPrice': .5, 'currentValue': 230}], [], profile={'pnl': 200})
    assert stats['resolved_positions_count'] == 0
    assert stats['unrealized_open_pnl'] == 180


def test_99_percent_wins_can_have_negative_expectancy():
    positions = [{'asset': str(i), 'realizedPnl': 1} for i in range(99)]
    positions.append({'asset': 'loss', 'realizedPnl': -200})
    stats = calculate_authentic_wallet_stats('a', [], [], profile={'pnl': 2000},
        closed_positions=positions, pnl_history=history())
    assert stats['win_rate_pct'] == 99
    assert stats['profit_factor'] == .495
    assert stats['expectancy_usd'] < 0
    stats['is_inactive_7d'] = False
    assert qualify_wallet(stats).rejection_reason == 'INSUFFICIENT_PAYOFF_AFTER_LOSSES'


def test_unredeemed_settled_loss_is_counted_without_inventing_outcomes():
    stats = calculate_authentic_wallet_stats('a', [{'asset': 'loser', 'redeemable': True,
        'size': 100, 'avgPrice': .8, 'curPrice': 0, 'realizedPnl': 0}], [],
        profile={'pnl': 20}, closed_positions=[{'asset': 'winner', 'realizedPnl': 100}])
    assert stats['win_rate_pct'] == 50
    assert stats['profit_factor'] == 1.25


def test_profile_and_chart_difference_is_not_rescaled():
    curve = history()
    stats = calculate_authentic_wallet_stats('a', [], [], profile={'pnl': 2}, pnl_history=curve)
    assert stats['daily_pnl_history'] == curve
    assert stats['cumulative_pnl'] == 1900
    assert stats['all_time_pnl_usd'] == 2


def test_payoff_and_consistency_outrank_raw_win_rate():
    stats = dict(history_verified=True, profile_verified=True, daily_pnl_history=history(),
        resolved_positions_count=200, all_time_pnl_usd=2000, expectancy_usd=10,
        profit_factor=2.5, max_drawdown_pct=5, outlier_concentration_pct=.1)
    assert qualify_wallet({**stats, 'win_rate_pct': 40}).status == 'active'
    assert quality_score(stats) > quality_score({**stats, 'win_rate_pct': 99, 'profit_factor': 1.3})
    assert qualify_wallet({**stats, 'daily_pnl_history': []}).status == 'rejected'


@pytest.mark.asyncio
async def test_profile_endpoint_and_failure_contract():
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(return_value=[{'t': 1700000000, 'p': 123}])
    try:
        assert (await client.fetch_wallet_pnl('0xABC'))[0]['cumulative_pnl'] == 123
        client._fetch_with_retry.assert_awaited_once_with('https://user-pnl-api.polymarket.com/user-pnl',
            {'user_address': '0xabc', 'interval': 'all', 'fidelity': '1d'})
        client._fetch_with_retry.return_value = None
        with pytest.raises(ProviderCoverageError):
            await client.fetch_wallet_pnl('0xABC')
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_closed_history_cap_is_not_complete():
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(return_value=[{'proxyWallet': 'a', 'asset': str(i)} for i in range(50)])
    try:
        with pytest.raises(ProviderCoverageError, match='cap reached'):
            await client.fetch_wallet_closed_positions('a', max_items=50)
    finally:
        await client.close()
