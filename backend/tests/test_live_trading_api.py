import uuid
from datetime import datetime
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.database import SessionLocal, init_db
from app.models import User, LiveWalletLink, ExecutionLog


@pytest.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    test_user_email = "livetrader_test@baleen.ai"
    async with SessionLocal() as db:
        # Check if test user exists
        stmt = select(User).where(User.email == test_user_email)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if not user:
            user = User(
                email=test_user_email,
                password_hash="testpass",
                sandbox_balance_usd=10000.0,
                sandbox_starting_balance_usd=10000.0,
                live_trading_enabled=False
            )
            db.add(user)
            await db.commit()
    yield
    async with SessionLocal() as db:
        stmt = select(User).where(User.email == test_user_email)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if user:
            await db.execute(delete(LiveWalletLink).where(LiveWalletLink.user_id == user.id))
            await db.execute(delete(ExecutionLog).where(ExecutionLog.user_id == user.id))
            await db.execute(delete(User).where(User.id == user.id))
            await db.commit()


@pytest.mark.asyncio
async def test_save_and_get_credentials():
    test_addr = "0x" + "1" * 40
    test_key = "abc-1234-defg-5678"
    test_secret = "secret-super-key"
    test_passphrase = "my-secret-passphrase"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Invalid address returns 400
        res_invalid = await ac.post("/api/live-trading/credentials", json={
            "polymarket_wallet_address": "invalid_address",
            "clob_api_key": test_key,
            "clob_api_secret": test_secret,
            "clob_api_passphrase": test_passphrase
        })
        assert res_invalid.status_code == 400

        # 2. Save valid credentials
        res_save = await ac.post("/api/live-trading/credentials", json={
            "polymarket_wallet_address": test_addr,
            "clob_api_key": test_key,
            "clob_api_secret": test_secret,
            "clob_api_passphrase": test_passphrase
        })
        assert res_save.status_code == 200
        data_save = res_save.json()
        assert data_save["success"] is True
        assert data_save["is_configured"] is True
        assert data_save["polymarket_wallet_address"] == test_addr.lower()
        assert data_save["clob_api_key_masked"] == "abc-...5678"

        # 3. GET credentials returns masked details
        res_get = await ac.get("/api/live-trading/credentials")
        assert res_get.status_code == 200
        data_get = res_get.json()
        assert data_get["is_configured"] is True
        assert data_get["polymarket_wallet_address"] == test_addr.lower()
        assert data_get["clob_api_key_masked"] == "abc-...5678"


@pytest.mark.asyncio
async def test_test_connection_and_balance():
    test_addr = "0x" + "2" * 40
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Save credentials first
        await ac.post("/api/live-trading/credentials", json={
            "polymarket_wallet_address": test_addr,
            "clob_api_key": "testkey12345678",
            "clob_api_secret": "testsecret",
            "clob_api_passphrase": "testpassphrase"
        })

        # Test connection
        res = await ac.post("/api/live-trading/test-connection", json={
            "polymarket_wallet_address": test_addr
        })
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["balance_usdc"] > 0
        assert data["wallet_address"] == test_addr.lower()


@pytest.mark.asyncio
async def test_toggle_live_trading():
    test_addr = "0x" + "3" * 40
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # When unconfigured, toggle should be rejected if user tries to enable
        # Let's test with a fresh user or ensure no credentials yet:
        # First save credentials
        await ac.post("/api/live-trading/credentials", json={
            "polymarket_wallet_address": test_addr,
            "clob_api_key": "key-1234567890",
            "clob_api_secret": "secret",
            "clob_api_passphrase": "pass"
        })

        # Enable live trading
        res_on = await ac.post("/api/live-trading/toggle", json={"enabled": True})
        assert res_on.status_code == 200
        data_on = res_on.json()
        assert data_on["is_live_active"] is True
        assert "Active" in data_on["status"]

        # Disable live trading
        res_off = await ac.post("/api/live-trading/toggle", json={"enabled": False})
        assert res_off.status_code == 200
        data_off = res_off.json()
        assert data_off["is_live_active"] is False


@pytest.mark.asyncio
async def test_live_trading_dashboard():
    test_addr = "0x" + "4" * 40
    async with SessionLocal() as db:
        stmt = select(User).order_by(User.created_at.asc()).limit(1)
        user = (await db.execute(stmt)).scalars().first()

        # Link wallet with live balance
        link = LiveWalletLink(
            user_id=user.id,
            provider="polymarket_clob",
            provider_user_id=test_addr,
            polymarket_wallet_address=test_addr,
            clob_api_key_enc="clob_key_dashboard_test",
            clob_api_secret_enc="clob_secret",
            clob_api_passphrase_enc="clob_pass",
            is_live_active=True,
            live_balance_usdc=5420.50,
            last_verified_at=datetime.utcnow()
        )
        db.add(link)

        # Create live execution log (is_sandbox = False)
        live_log = ExecutionLog(
            user_id=user.id,
            source_wallet_address="0xwhale123",
            market_question="Will ETH surpass $4,000 in Q3?",
            market_condition_id="0xconditionEth",
            resolution_outcome="Yes",
            side="BUY",
            whale_entry_price=0.45,
            user_fill_price=0.45,
            notional_usd=150.0,
            status="FILLED",
            is_sandbox=False,
            executed_at=datetime.utcnow()
        )
        # Create sandbox execution log (is_sandbox = True, should NOT appear in live dashboard)
        sandbox_log = ExecutionLog(
            user_id=user.id,
            source_wallet_address="0xwhaleSandbox",
            market_question="Sandbox Test Market",
            side="BUY",
            status="FILLED",
            is_sandbox=True,
            executed_at=datetime.utcnow()
        )
        db.add(live_log)
        db.add(sandbox_log)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/live-trading/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert data["is_configured"] is True
        assert data["is_live_active"] is True
        assert data["usdc_balance"] == 5420.50
        assert data["open_positions_value"] >= 150.0
        assert data["portfolio_net_worth"] == round(data["usdc_balance"] + data["open_positions_value"], 2)

        # Ensure execution logs only include live logs (isSandbox == False)
        for log in data["execution_logs"]:
            assert log["isSandbox"] is False

        # Ensure active position is present
        positions = [p for p in data["active_positions"] if p["conditionId"] == "0xconditionEth"]
        assert len(positions) == 1
        assert positions[0]["notionalUsd"] == 150.0
