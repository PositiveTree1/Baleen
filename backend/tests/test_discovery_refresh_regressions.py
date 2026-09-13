import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import Wallet, WalletSnapshot
from app.discovery import scanner


@pytest.mark.asyncio
async def test_full_refresh_preserves_tracked_wallets_and_snapshots(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    class EmptyClient:
        async def discover_candidates(self):
            return {}

        async def close(self):
            return None

    monkeypatch.setattr(scanner, "PolymarketClient", EmptyClient)
    monkeypatch.setattr("app.discovery.curated_whales.CURATED_WHALE_ADDRESSES", [])

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            wallet = Wallet(address="0xtracked", status="active", all_time_pnl_usd=123.0)
            db.add(wallet)
            db.add(WalletSnapshot(wallet_address=wallet.address, pnl_usd=123.0, baleen_score=80.0))
            await db.commit()

            await scanner.scan_for_wallets(db, full_refresh=True)

            assert await db.get(Wallet, wallet.address) is not None
            assert (await db.execute(
                select(WalletSnapshot).where(WalletSnapshot.wallet_address == wallet.address)
            )).scalars().first() is not None
    finally:
        await engine.dispose()
