import uuid
from decimal import Decimal
from datetime import datetime
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.database import SessionLocal, init_db
from app.models import User, LiveWalletLink, ExecutionLog, LiveExecutionAccount
from app.auth import get_current_user, get_current_user_optional


@pytest.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    test_user_email = "livetrader_test@baleen.ai"
    user = None
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
            await db.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_user_optional] = lambda: user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_optional, None)
    async with SessionLocal() as db:
        stmt = select(User).where(User.email == test_user_email)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if user:
            await db.execute(delete(LiveExecutionAccount).where(LiveExecutionAccount.user_id == user.id))
            await db.execute(delete(LiveWalletLink).where(LiveWalletLink.user_id == user.id))
            await db.execute(delete(ExecutionLog).where(ExecutionLog.user_id == user.id))
            await db.execute(delete(User).where(User.id == user.id))
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['disable', 'rotate'])
async def test_disable_and_credential_rotation_stop_order_account_preserving_reservations(operation):
    async with SessionLocal() as db, db.begin():
        user = (await db.execute(select(User).where(User.email == 'livetrader_test@baleen.ai'))).scalar_one()
        uid = user.id
        db.add(LiveWalletLink(user_id=uid, polymarket_wallet_address='0x' + '1' * 40,
            signer_address='0x' + '1' * 40, signature_type=0, clob_api_key_enc='fixture-original'))
        db.add(LiveExecutionAccount(user_id=uid, run_id=uuid.uuid4(), wallet_address='0x' + '1' * 40,
            cash=100, reserved_cash=50, enabled=True, reconciled_at=datetime.utcnow()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        if operation == 'disable':
            response = await ac.post('/api/live-trading/toggle', json={'enabled': False})
        else:
            response = await ac.post('/api/live-trading/credentials', json={
                'polymarket_wallet_address': '0x' + '1' * 40,
                'clob_api_key': 'fixture', 'clob_api_secret': 'fixture', 'clob_api_passphrase': 'fixture'})
        assert response.status_code == 200
        state = (await ac.get('/api/live-trading/execution-state')).json()
        assert Decimal(state['cash']) == 100 and Decimal(state['reservedCash']) == 50
        assert state['liveExecutionReady'] is False
        assert 'envelope' not in str(state)
    async with SessionLocal() as db:
        account = await db.get(LiveExecutionAccount, uid)
        assert not account.enabled and account.reserved_cash == 50


@pytest.mark.asyncio
async def test_execution_state_does_not_invent_cash_or_live_readiness():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        state = (await ac.get('/api/live-trading/execution-state')).json()
        assert state['status'] == 'unavailable' and state['cash'] is None
        capabilities = (await ac.get('/api/live-trading/capabilities')).json()
        assert not capabilities['live_execution_ready'] and not capabilities['credentials_verified']


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
async def test_test_connection_and_balance(monkeypatch):
    from decimal import Decimal
    from unittest.mock import AsyncMock
    from app.services.clob_gateway import ClobGateway
    monkeypatch.setattr(ClobGateway, 'collateral_balance', AsyncMock(return_value={
        'balance': Decimal('0'), 'allowances': {}, 'source': 'authenticated_clob'}))
    test_addr = "0x" + "2" * 40
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Save credentials first
        await ac.post("/api/live-trading/credentials", json={
            "polymarket_wallet_address": test_addr,
            "clob_api_key": "testkey12345678",
            "clob_api_secret": "testsecret",
            "clob_api_passphrase": "testpassphrase",
            "signer_address": test_addr,
            "signature_type": 0
        })

        # Test connection
        res = await ac.post("/api/live-trading/test-connection", json={
            "polymarket_wallet_address": test_addr
        })
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["balance_usdc"] == 0.0
        assert data['live_execution_ready'] is False
        assert data["wallet_address"] == test_addr.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize('bound', [False, True])
async def test_deposit_wallet_balance_requires_authenticated_wallet_identity(monkeypatch, bound):
    from unittest.mock import AsyncMock
    from app.services.clob_gateway import ClobGateway
    wallet = '0x'+'2'*40
    monkeypatch.setattr(ClobGateway, 'collateral_balance', AsyncMock(return_value={
        'balance':Decimal('27.25'), 'allowances':{}, 'source':'authenticated_clob'}))
    monkeypatch.setattr(ClobGateway, '_get', AsyncMock(return_value={
        'wallet':wallet if bound else '0x'+'4'*40, 'signers':[]}))
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/api/live-trading/test-connection', json={
            'polymarket_wallet_address':wallet, 'signer_address':'0x'+'3'*40, 'signature_type':3,
            'clob_api_key':'fixture', 'clob_api_secret':'fixture', 'clob_api_passphrase':'fixture'})
        assert response.status_code == 200
        assert response.json()['wallet_binding_verified'] == bound
        assert response.json()['balance_usdc'] == (27.25 if bound else None)


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

        # 1. When LIVE_EXECUTION_ENABLED is False (default), enabling live trading MUST return 400
        from app.config import settings
        orig_live_flag = getattr(settings, "LIVE_EXECUTION_ENABLED", False)
        settings.LIVE_EXECUTION_ENABLED = False
        try:
            res_blocked = await ac.post("/api/live-trading/toggle", json={"enabled": True})
            assert res_blocked.status_code == 400
            assert "Live exchange execution is currently disabled" in res_blocked.json()["detail"]

            # A flag cannot turn the paper simulator into a verified exchange adapter.
            settings.LIVE_EXECUTION_ENABLED = True
            res_on = await ac.post("/api/live-trading/toggle", json={"enabled": True})
            assert res_on.status_code == 409
            assert 'reconciliation' in res_on.json()['detail']

            # 3. Disable live trading
            res_off = await ac.post("/api/live-trading/toggle", json={"enabled": False})
            assert res_off.status_code == 200
            data_off = res_off.json()
            assert data_off["is_live_active"] is False
        finally:
            settings.LIVE_EXECUTION_ENABLED = orig_live_flag


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
        assert data["is_live_active"] is False
        assert data['usdc_balance'] is None and data['portfolio_net_worth'] is None
        assert data['open_positions_value'] is None and data['live_pnl'] is None
        assert data['execution_logs'] == [] and data['active_positions'] == []
        assert data['execution_evidence'] == 'legacy_unverified'
        records = [r for r in data['legacy_records'] if r['marketConditionId'] == '0xconditionEth']
        assert len(records) == 1 and records[0]['size'] == 150.0
        assert all(r['evidence'] == 'legacy_unverified' for r in data['legacy_records'])
