import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import SessionLocal, init_db
from app.models import Wallet, WalletSnapshot, WalletEvidence

@pytest.mark.asyncio
async def test_get_wallet_detail_and_snapshots():
    await init_db()
    import uuid
    test_addr = f"0x{uuid.uuid4().hex}"
    
    async with SessionLocal() as db:
        w = Wallet(
            address=test_addr,
            status="active",
            tier="gold_sniper",
            win_rate_pct=88.5,
            all_time_pnl_usd=125000.0,
            avg_trades_per_day=6.2,
            max_drawdown_pct=5.1,
            baleen_score=91.0,
            ai_summary="High conviction prediction market sniper.",
            ai_style_tag="GOLD SNIPER",
            cached_daily_pnl='[{"date":"2026-08-28","net_pnl":100.0},{"date":"2026-08-29","net_pnl":200.0},{"date":"2026-08-30","net_pnl":300.0}]'
        )
        snap = WalletSnapshot(
            wallet_address=test_addr,
            baleen_score=91.0,
            win_rate_pct=88.5,
            pnl_usd=125000.0
        )
        db.add(w)
        db.add(snap)
        await db.commit()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get(f"/api/wallets/{test_addr}")
            assert res.status_code == 200
            data = res.json()
            assert data["wallet"]["address"] == test_addr
            assert data["wallet"]["tier"] == "gold_sniper"
            assert len(data["score_history"]) >= 1
            # An unproven legacy cache is not a provider account P&L series.
            assert data["daily_pnl_history"] == []
            assert data["pnl_metadata"]["status"] == "unavailable"
            assert data["wallet"]["max_drawdown_pct"] is None
            assert data["wallet"]["ai_summary"] is not None
    finally:
        async with SessionLocal() as db:
            from sqlalchemy import delete
            await db.execute(delete(WalletSnapshot).where(WalletSnapshot.wallet_address == test_addr))
            await db.execute(delete(Wallet).where(Wallet.address == test_addr))
            await db.commit()


@pytest.mark.asyncio
async def test_metadata_refresh_does_not_repopulate_reset_statistics(monkeypatch):
    import uuid
    from unittest.mock import AsyncMock
    from sqlalchemy import delete
    await init_db()
    address = '0x' + uuid.uuid4().hex + '0'*8
    client = AsyncMock()
    client.fetch_wallet_profile.return_value = {'name':'Fresh name', 'pnl':999999, 'reported_period':'ALL'}
    monkeypatch.setattr('app.discovery.polymarket_client.PolymarketClient', lambda: client)
    monkeypatch.setattr('app.discovery.wallet_evidence.pnl_series', AsyncMock(return_value=None))
    async with SessionLocal() as db:
        db.add(Wallet(address=address, status='tracked'))
        await db.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
            response = await ac.get('/api/wallets/' + address)
            assert response.status_code == 200
            assert response.json()['wallet']['all_time_pnl_usd'] is None
        async with SessionLocal() as db:
            wallet = await db.get(Wallet, address)
            assert wallet.name == 'Fresh name'
            assert wallet.all_time_pnl_usd is None and wallet.last_scored_at is None
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(Wallet).where(Wallet.address == address))
            await db.commit()


@pytest.mark.asyncio
async def test_verified_evidence_immediately_populates_wallet_stats_and_curve(monkeypatch):
    import uuid
    from datetime import datetime
    from unittest.mock import AsyncMock
    from sqlalchemy import delete
    from app.discovery.wallet_evidence import POLICY_VERSION
    from app.services.wallet_reset import current_generation
    await init_db()
    address = '0x' + uuid.uuid4().hex + '0' * 8
    live_curve = AsyncMock(return_value=None)
    monkeypatch.setattr('app.discovery.wallet_evidence.pnl_series', live_curve)
    async with SessionLocal() as db:
        generation = await current_generation(db)
        db.add(Wallet(address=address, status='tracked', name='Verified candidate'))
        db.add(WalletEvidence(wallet_address=address, observed_at=datetime.utcnow(), payload={
            'policy_version': POLICY_VERSION, 'generation': generation, 'classification': 'research_candidate',
            'reasons': ['ACCOUNT_REPLAY_AND_FORWARD_VALIDATION_REQUIRED'],
            'metrics': {'economic_pnl': 125000, 'closed_position_win_rate_pct': 82.5,
                        'closed_position_profit_factor': 3.2, 'fills_per_day_30d': 4.5,
                        'median_inter_fill_gap_hours': 5.25, 'evidence_quality_score': 88.1,
                        'max_daily_fills': 8, 'fills_per_day_7d': 4.0, 'distinct_markets_lifetime': 50},
            'daily_pnl_history': [{'date': '2026-09-22', 'daily_pnl': None, 'net_pnl': None,
                                   'cumulative_pnl': 124000, 'won_usd': None, 'lost_usd': None,
                                   'trades_count': None},
                                  {'date': '2026-09-23', 'daily_pnl': 1000, 'net_pnl': 1000,
                                   'cumulative_pnl': 125000, 'won_usd': 1000, 'lost_usd': 0,
                                   'trades_count': None}]}))
        await db.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
            response = await ac.get('/api/wallets/' + address)
        assert response.status_code == 200
        body = response.json()
        assert body['wallet']['win_rate_pct'] == 82.5
        assert body['wallet']['baleen_score'] == 88.1
        assert body['wallet']['median_inter_trade_gap_hours'] == 5.25
        assert body['pnl_metadata']['status'] == 'cached'
        assert len(body['daily_pnl_history']) == 2
        live_curve.assert_not_awaited()
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(WalletEvidence).where(WalletEvidence.wallet_address == address))
            await db.execute(delete(Wallet).where(Wallet.address == address))
            await db.commit()


@pytest.mark.asyncio
async def test_default_wallet_list_returns_fresh_verified_candidates():
    """The dashboard list must not depend on database-specific JSON SQL."""
    import uuid
    from datetime import datetime
    from sqlalchemy import delete
    from app.discovery.wallet_evidence import POLICY_VERSION
    from app.services.wallet_reset import current_generation

    await init_db()
    address = '0x' + uuid.uuid4().hex + '0' * 8
    async with SessionLocal() as db:
        generation = await current_generation(db)
        db.add(Wallet(address=address, status='tracked', all_time_pnl_usd=100000))
        db.add(WalletEvidence(wallet_address=address, observed_at=datetime.utcnow(), payload={
            'policy_version': POLICY_VERSION,
            'generation': generation,
            'classification': 'research_candidate',
            'reasons': ['ACCOUNT_REPLAY_AND_FORWARD_VALIDATION_REQUIRED'],
            'metrics': {'economic_pnl': 100000, 'fills_per_day_30d': 5,
                        'closed_position_win_rate_pct': 80, 'evidence_quality_score': 85},
        }))
        await db.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/api/wallets?limit=10')
        assert response.status_code == 200
        row = next(wallet for wallet in response.json() if wallet['address'] == address)
        assert row['baleen_score'] == 85
        assert row['win_rate_pct'] == 80
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(WalletEvidence).where(WalletEvidence.wallet_address == address))
            await db.execute(delete(Wallet).where(Wallet.address == address))
            await db.commit()
