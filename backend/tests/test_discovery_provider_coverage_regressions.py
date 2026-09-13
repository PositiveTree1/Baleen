import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.discovery.polymarket_client import ProviderCoverageError, ProviderListResult
from app.discovery.scanner import evaluate_pending_wallets
from app.models import ExecutionLog, Wallet


class IncompleteClient:
    async def _incomplete(self, *args, **kwargs):
        raise ProviderCoverageError(
            "incomplete history", ProviderListResult([], reason="page timeout")
        )

    async def fetch_wallet_positions(self, *args, **kwargs):
        return await self._incomplete()

    async def fetch_wallet_activity(self, *args, **kwargs):
        return await self._incomplete()

    async def fetch_wallet_profile(self, *args, **kwargs):
        return await self._incomplete()

    async def fetch_wallet_trades(self, *args, **kwargs):
        return await self._incomplete()

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_incomplete_provider_history_cannot_improve_or_erase_wallet_metrics():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    address = "0xcoverage"
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            wallet = Wallet(address=address, status="pending", tier="standard",
                            all_time_pnl_usd=12345.0, total_trades_analyzed=222,
                            baleen_score=88.0)
            db.add(wallet)
            await db.commit()

            processed = await evaluate_pending_wallets(db, client=IncompleteClient())
            await db.refresh(wallet)

            assert processed == 1
            assert wallet.status == "rejected"
            assert "Insufficient provider coverage" in wallet.rejection_reason
            assert wallet.all_time_pnl_usd == 12345.0
            assert wallet.total_trades_analyzed == 222
            assert wallet.baleen_score == 88.0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_incomplete_refresh_tracks_wallet_with_open_position_for_exit_continuity():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    address = "0xcoverageheld"
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add(Wallet(address=address, status="pending", tier="gold_sniper"))
            db.add(ExecutionLog(
                source_wallet_address=address, market_condition_id="condition",
                market_question="test", side="BUY", whale_entry_price=0.5,
                user_fill_price=0.5, notional_usd=10.0, active_basket_size_at_trade=1,
                is_sandbox=True, status="FILLED", fee_usd=0.0,
            ))
            await db.commit()

            await evaluate_pending_wallets(db, client=IncompleteClient())
            wallet = await db.get(Wallet, address)
            assert wallet.status == "tracked"
            assert wallet.tier == "gold_sniper"
            assert "Insufficient provider coverage" in wallet.rejection_reason
    finally:
        await engine.dispose()
