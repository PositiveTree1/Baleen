import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

@pytest.mark.asyncio
async def test_signals_and_trade_endpoints():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/health")
        assert res.status_code == 200

        # 2. Executions list
        res = await client.get("/api/executions?limit=10")
        assert res.status_code == 200
        logs = res.json()
        assert isinstance(logs, list)

        # 3. Portfolio summary with timeframes
        for tf in ["1d", "1w", "1m", "ytd", "all"]:
            res = await client.get(f"/api/executions/summary?timeframe={tf}")
            assert res.status_code == 200
            summary = res.json()
            assert "startingBalance" in summary
            assert "currentBalance" in summary
            assert "totalPnlUsd" in summary

        # 4. Snapshots with timeframes
        for tf in ["1d", "1w", "1m", "ytd"]:
            res = await client.get(f"/api/executions/snapshots?timeframe={tf}")
            assert res.status_code == 200
            snapshots = res.json()
            assert isinstance(snapshots, list)

        # 5. Ingest on-chain HyperSync signal
        signal_payload = {
            "walletAddress": "0x1234567890abcdef1234567890abcdef12345678",
            "side": "BUY",
            "assetId": "9123847291823749812739812",
            "amountFilled": "100000000",
            "price": "0.485",
            "transactionHash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "logIndex": 1,
            "blockNumber": 68000000,
            "timestamp": 1787144000000
        }
        res = await client.post("/api/signals", json=signal_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "queued"
