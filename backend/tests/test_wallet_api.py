import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import SessionLocal, init_db
from app.models import Wallet, WalletSnapshot

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
            assert len(data["daily_pnl_history"]) == 3
            assert data["wallet"]["ai_summary"] is not None
    finally:
        async with SessionLocal() as db:
            from sqlalchemy import delete
            await db.execute(delete(WalletSnapshot).where(WalletSnapshot.wallet_address == test_addr))
            await db.execute(delete(Wallet).where(Wallet.address == test_addr))
            await db.commit()
