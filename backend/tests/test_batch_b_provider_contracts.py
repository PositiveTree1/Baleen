import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import httpx

from app.discovery.polymarket_client import PolymarketClient, ProviderResponseStatus, ProviderCoverageError


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['fetch_wallet_positions', 'fetch_wallet_trades', 'fetch_wallet_activity', 'fetch_wallet_closed_positions'])
async def test_first_page_outage_is_not_an_empty_wallet(method):
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(return_value=None)
    try:
        with pytest.raises(ProviderCoverageError) as error:
            await getattr(client, method)('0x' + '1' * 40)
        assert error.value.result.status == ProviderResponseStatus.UNAVAILABLE
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_wrong_market_price_rejected():
    """
    R3 Invariant: When fetching live prices for a specific condition ID,
    if the provider returns an unrelated market/condition, it MUST be rejected
    and NOT attached to the requested condition ID.
    """
    cid = "0x" + "b" * 64
    wrong_cid = "0x" + "d" * 64

    client = PolymarketClient()
    # Mock Gamma response returning a market with a different conditionId
    client._fetch_with_retry = AsyncMock(side_effect=[
        [],  # Bulk active markets return empty
        [{"conditionId": wrong_cid, "outcomes": ["Yes", "No"], "outcomePrices": ["0.9", "0.1"]}]  # Targeted fetch returns wrong market
    ])

    prices = await client.fetch_batch_live_prices([cid])
    assert cid not in prices, f"Mismatched condition ID {wrong_cid} was falsely accepted for {cid}"
    assert prices.get(cid) is None
    await client.close()


@pytest.mark.asyncio
async def test_wrong_wallet_rejected_in_positions():
    """
    R3 Invariant: When fetching wallet positions, items returning an unrelated wallet
    must be filtered out and never attributed to the requested wallet.
    """
    requested_wallet = "0x" + "1" * 40
    unrelated_wallet = "0x" + "2" * 40

    client = PolymarketClient()
    mock_payload = [
        {"user": requested_wallet, "asset": "111", "cashPnl": 50.0},
        {"user": unrelated_wallet, "asset": "222", "cashPnl": 999.0},  # Mismatched identity
    ]
    client._fetch_with_retry = AsyncMock(return_value=mock_payload)

    positions = await client.fetch_wallet_positions(requested_wallet)
    assert len(positions) == 1
    assert positions[0]["asset"] == "111"
    assert positions[0]["user"] == requested_wallet
    await client.close()


@pytest.mark.asyncio
async def test_missing_wallet_identity_rejected_in_positions():
    """Rows without provider identity must not be attributed to the requested wallet."""
    requested_wallet = "0x" + "4" * 40
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(return_value=[{"asset": "unscoped", "cashPnl": 999.0}])
    assert await client.fetch_wallet_positions(requested_wallet) == []
    await client.close()


@pytest.mark.asyncio
async def test_wrong_wallet_rejected_in_trades():
    """
    R3 Invariant: Wallet trades query must reject rows from mismatched wallets.
    """
    requested_wallet = "0x" + "a" * 40
    unrelated_wallet = "0x" + "b" * 40

    client = PolymarketClient()
    mock_payload = [
        {"user": requested_wallet, "asset": "111", "side": "BUY", "price": 0.5, "size": 100},
        {"user": unrelated_wallet, "asset": "222", "side": "BUY", "price": 0.8, "size": 500},
    ]
    client._fetch_with_retry = AsyncMock(return_value=mock_payload)

    trades = await client.fetch_wallet_trades(requested_wallet, max_trades=10)
    assert len(trades) == 1
    assert trades[0]["user"] == requested_wallet
    await client.close()


@pytest.mark.asyncio
async def test_valid_zero_pnl_survives():
    """
    R3 Invariant: Valid 0.0 PnL from profile or positions must survive
    and not be treated as missing or replaced with defaults.
    """
    addr = "0x" + "3" * 40
    client = PolymarketClient()

    # Profile returns explicit 0.0 profit
    client.fetch_wallet_profile = AsyncMock(return_value={
        "user": addr,
        "profit": 0.0,
        "pnl": 0.0,
        "reported_period": "ALL"
    })
    client.fetch_wallet_positions = AsyncMock(return_value=[])

    pnl = await client.fetch_wallet_profile_pnl(addr)
    assert pnl == 0.0, f"Expected 0.0, got {pnl}"
    await client.close()


@pytest.mark.asyncio
async def test_fetch_with_retry_bounded_on_rate_limit():
    """
    R3 Invariant: 429 rate limit triggers backoff retries bounded by retry limit.
    """
    client = PolymarketClient()

    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = httpx.Response(
            status_code=429,
            headers={"Retry-After": "0.01"},
            request=httpx.Request("GET", "http://test")
        )
        return resp

    client.client.get = mock_get
    result = await client._fetch_with_retry("http://test/endpoint")
    assert result is None
    assert call_count == 3  # Exactly 3 retries, bounded
    await client.close()


@pytest.mark.asyncio
async def test_fetch_with_retry_permanent_error_fails_closed():
    """
    R3 Invariant: Permanent errors (400/404) fail closed immediately without retry loop.
    """
    client = PolymarketClient()

    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=404, request=httpx.Request("GET", "http://test"))

    client.client.get = mock_get
    result = await client._fetch_with_retry("http://test/missing")
    assert result is None
    assert call_count == 1  # No repeated retries for 404
    await client.close()


@pytest.mark.asyncio
async def test_token_resolution_does_not_guess_first_token_for_unknown_outcome():
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(return_value=[{
        "conditionId": "0x" + "a" * 64,
        "outcomes": ["Yes", "No"],
        "clobTokenIds": ["101", "202"],
    }])
    assert await client.get_token_id_for_condition("0x" + "a" * 64, "Unknown") is None
    await client.close()


@pytest.mark.asyncio
async def test_trade_page_two_failure_raises_with_partial_result():
    wallet = "0x" + "5" * 40
    page = [{"user": wallet, "asset": str(i), "price": 0.5} for i in range(500)]
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(side_effect=[page, None])
    with pytest.raises(ProviderCoverageError) as exc:
        await client.fetch_wallet_trades(wallet, max_trades=1000)
    assert len(exc.value.result) == 500
    assert exc.value.result.status == ProviderResponseStatus.PARTIAL
    await client.close()


@pytest.mark.asyncio
async def test_trade_repeated_page_raises_instead_of_looping_or_returning_success():
    wallet = "0x" + "6" * 40
    page = [{"user": wallet, "asset": str(i), "price": 0.5} for i in range(500)]
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(side_effect=[page, page])
    with pytest.raises(ProviderCoverageError, match="repeated page"):
        await client.fetch_wallet_trades(wallet, max_trades=1000)
    await client.close()
