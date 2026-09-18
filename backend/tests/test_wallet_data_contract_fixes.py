from unittest.mock import AsyncMock

import pytest

from app.discovery.polymarket_client import PolymarketClient

ADDRESS = "0x" + "a" * 40


@pytest.mark.asyncio
async def test_discovery_visits_each_of_first_300_leaderboard_ranks():
    client = PolymarketClient()
    async def provider(url, params):
        if url.endswith('/v1/leaderboard'):
            return [{'proxyWallet': '0x' + format(i, '040x'), 'pnl': 60000, 'vol': 0}
                    for i in range(params['offset'] + 1, params['offset'] + 51)]
        return []
    client._fetch_with_retry = AsyncMock(side_effect=provider)
    try:
        result = await client.discover_candidates()
        assert len(result) == 300
        assert all(w['volume'] == 0 for w in result.values())
        calls = [c.args[1] for c in client._fetch_with_retry.call_args_list if c.args[0].endswith('/v1/leaderboard')]
        for period in ['ALL','MONTH','WEEK']:
            assert [p['offset'] for p in calls if p['timePeriod'] == period] == [0,50,100,150,200,250]
            assert all(p['limit'] == 50 for p in calls)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_single_trade_does_not_become_estimated_wallet_volume():
    client = PolymarketClient()
    async def provider(url, params):
        return [{'proxyWallet': ADDRESS, 'size': 20, 'price': 0.5}] if url.endswith('/trades') else []
    client._fetch_with_retry = AsyncMock(side_effect=provider)
    try:
        candidate = (await client.discover_candidates())[ADDRESS]
        assert candidate['trade_cash'] == 10
        assert candidate['volume'] is None
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('profile', [None, {'pnl': 100000, 'reported_period': 'MONTH'}, {'pnl': float('nan'), 'reported_period': 'ALL'}])
async def test_unknown_lifetime_pnl_never_uses_open_positions(profile):
    client = PolymarketClient()
    client.fetch_wallet_profile = AsyncMock(return_value=profile)
    client.fetch_wallet_positions = AsyncMock(return_value=[{'cashPnl': 999999}])
    try:
        assert await client.fetch_wallet_profile_pnl(ADDRESS) is None
        client.fetch_wallet_positions.assert_not_called()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_profile_never_falls_back_to_monthly_pnl():
    client = PolymarketClient()
    async def provider(url, params):
        if params.get('timePeriod') == 'MONTH':
            return [{'proxyWallet': ADDRESS, 'pnl': 999999}]
        return []
    client._fetch_with_retry = AsyncMock(side_effect=provider)
    try:
        assert await client.fetch_wallet_profile(ADDRESS) is None
        assert not any(c.args[1].get('timePeriod') == 'MONTH' for c in client._fetch_with_retry.call_args_list if len(c.args)>1)
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['fetch_wallet_trades','fetch_wallet_activity'])
async def test_paginated_feed_pins_cutoff_and_includes_makers(method):
    client = PolymarketClient()
    page = [{'proxyWallet':ADDRESS,'timestamp':1000+i} for i in range(500)]
    client._fetch_with_retry = AsyncMock(side_effect=[page, []])
    try:
        result = await getattr(client, method)(ADDRESS)
        assert len(result) == 500
        params = [c.kwargs['params'] for c in client._fetch_with_retry.call_args_list]
        assert params[0]['end'] == params[1]['end']
        assert params[0]['end'] > 1000
        assert params[1]['offset'] == 500
        if method == 'fetch_wallet_trades':
            assert all(p['takerOnly'] == 'false' for p in params)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_closed_positions_use_documented_sort_enum():
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(return_value=[])
    try:
        await client.fetch_wallet_closed_positions(ADDRESS)
        assert client._fetch_with_retry.call_args.kwargs['params']['sortBy'] == 'TIMESTAMP'
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('data', [{'data':None}, {'data':{'proxy_wallet':'0xwrong','trades':10}}])
async def test_user_stats_miss_or_wrong_identity_is_unknown(data):
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(return_value=data)
    try:
        assert await client.fetch_wallet_user_stats(ADDRESS) is None
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_lifetime_threshold_is_not_rounded_up():
    client = PolymarketClient()
    client.fetch_wallet_profile = AsyncMock(return_value={'pnl':49999.999,'reported_period':'ALL'})
    try:
        assert await client.fetch_wallet_profile_pnl(ADDRESS) < 50000
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_discovery_pnl_gate_precedes_storage_and_deep_evaluation(monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.database import Base
    from app.models import Wallet
    from app.discovery import scanner

    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    addresses = ['0x' + format(i,'040x') for i in range(1,7)]
    values = dict(zip(addresses,[49999.99,50000.0,None,float('nan'),float('inf'),0.0]))
    client = AsyncMock()
    client.discover_candidates.return_value = {a:{'profit':999999} for a in addresses}
    client.fetch_wallet_profile_pnl.side_effect = lambda a: values[a]
    monkeypatch.setattr(scanner,'PolymarketClient',lambda:client)
    monkeypatch.setattr('app.discovery.curated_whales.CURATED_WHALE_ADDRESSES',[])
    observed=[]
    async def evaluate(db):
        observed.extend((await db.execute(select(Wallet.address))).scalars().all())
        return 0
    monkeypatch.setattr(scanner,'refresh_wallet_evidence',evaluate)
    monkeypatch.setattr(scanner,'_persist_discovery_state',AsyncMock())
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            await scanner.scan_for_wallets(db)
            assert observed == [addresses[1]]
            assert (await db.execute(select(Wallet.address))).scalars().all() == [addresses[1]]
            client.fetch_wallet_trades.assert_not_called()
    finally:
        await engine.dispose()
