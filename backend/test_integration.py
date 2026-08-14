"""
Real integration tests for Baleen backend.
Tests actual API connections and data flows.
"""
import asyncio
import httpx
import json

POLYMARKET_DATA_API = "https://data-api.polymarket.com"
POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_API = "https://clob.polymarket.com"
RENDER_BACKEND = "https://baleen-backend.onrender.com"

async def test_polymarket_leaderboard():
    """Test: What fields does the Polymarket leaderboard actually return?"""
    print("\n=== TEST 1: Polymarket Leaderboard ===")
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Try multiple endpoints
        for url in [
            f"{POLYMARKET_DATA_API}/leaderboard",
            f"{POLYMARKET_DATA_API}/v1/leaderboard",
            f"{POLYMARKET_GAMMA_API}/leaderboard",
        ]:
            try:
                res = await client.get(url, params={"window": "all", "limit": 3})
                print(f"\n  URL: {url}")
                print(f"  Status: {res.status_code}")
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        print(f"  Type: list, Count: {len(data)}")
                        print(f"  First entry keys: {list(data[0].keys())}")
                        print(f"  First entry: {json.dumps(data[0], indent=2)[:500]}")
                    elif isinstance(data, dict):
                        print(f"  Type: dict, Keys: {list(data.keys())}")
                        # Check if it's paginated
                        if "data" in data or "results" in data:
                            items = data.get("data") or data.get("results") or []
                            if items:
                                print(f"  Inner list count: {len(items)}")
                                print(f"  First entry keys: {list(items[0].keys())}")
                                print(f"  First entry: {json.dumps(items[0], indent=2)[:500]}")
                    else:
                        print(f"  Unexpected response type: {type(data)}")
                else:
                    print(f"  Body: {res.text[:200]}")
            except Exception as e:
                print(f"  URL: {url} -> ERROR: {e}")


async def test_polymarket_trades():
    """Test: What fields do Polymarket trades return?"""
    print("\n=== TEST 2: Polymarket Trades ===")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get(f"{POLYMARKET_DATA_API}/trades", params={"limit": 3})
            print(f"  Status: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    print(f"  Count: {len(data)}")
                    print(f"  Trade keys: {list(data[0].keys())}")
                    print(f"  First trade: {json.dumps(data[0], indent=2)[:500]}")
                elif isinstance(data, dict):
                    print(f"  Dict keys: {list(data.keys())}")
                    print(f"  Raw: {json.dumps(data, indent=2)[:500]}")
            else:
                print(f"  Body: {res.text[:200]}")
        except Exception as e:
            print(f"  ERROR: {e}")


async def test_polymarket_wallet_trades():
    """Test: Can we fetch trades for a specific known wallet?"""
    print("\n=== TEST 3: Polymarket Wallet-Specific Trades ===")
    # Use a known active Polymarket whale
    test_wallet = "0x1a1d6e8a3e2e6e0c13bf2d0f3a1595c7e2b2e3e4"
    async with httpx.AsyncClient(timeout=15.0) as client:
        for param_name in ["maker", "maker_address", "user"]:
            try:
                res = await client.get(
                    f"{POLYMARKET_DATA_API}/trades",
                    params={param_name: test_wallet, "limit": 2}
                )
                print(f"\n  Param '{param_name}': Status {res.status_code}")
                data = res.json()
                if isinstance(data, list):
                    print(f"  Results: {len(data)} trades")
                    if data:
                        print(f"  Keys: {list(data[0].keys())}")
                else:
                    print(f"  Response: {json.dumps(data, indent=2)[:200]}")
            except Exception as e:
                print(f"  Param '{param_name}': ERROR: {e}")


async def test_gamma_markets():
    """Test: Can we fetch market info from Gamma API?"""
    print("\n=== TEST 4: Gamma Markets API ===")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get(f"{POLYMARKET_GAMMA_API}/markets", params={"limit": 2, "active": True})
            print(f"  Status: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    print(f"  Count: {len(data)}")
                    print(f"  Market keys: {list(data[0].keys())}")
                    print(f"  First market question: {data[0].get('question', 'N/A')[:100]}")
                elif isinstance(data, dict):
                    print(f"  Dict keys: {list(data.keys())}")
            else:
                print(f"  Body: {res.text[:200]}")
        except Exception as e:
            print(f"  ERROR: {e}")


async def test_clob_orderbook():
    """Test: Can we fetch an order book from CLOB API?"""
    print("\n=== TEST 5: CLOB Order Book ===")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # First get a token_id from gamma
            markets_res = await client.get(f"{POLYMARKET_GAMMA_API}/markets", params={"limit": 1, "active": True})
            if markets_res.status_code == 200:
                markets = markets_res.json()
                if isinstance(markets, list) and markets:
                    token_ids = markets[0].get("clobTokenIds", [])
                    if token_ids:
                        token_id = token_ids[0] if isinstance(token_ids, list) else token_ids
                        print(f"  Using token_id: {str(token_id)[:50]}...")
                        book_res = await client.get(f"{POLYMARKET_CLOB_API}/book", params={"token_id": token_id})
                        print(f"  Book status: {book_res.status_code}")
                        if book_res.status_code == 200:
                            book = book_res.json()
                            print(f"  Book keys: {list(book.keys())}")
                            asks = book.get("asks", [])
                            bids = book.get("bids", [])
                            print(f"  Asks: {len(asks)} levels, Bids: {len(bids)} levels")
                            if asks:
                                print(f"  Ask level keys: {list(asks[0].keys())}")
                        else:
                            print(f"  Book body: {book_res.text[:200]}")
                    else:
                        print(f"  No clobTokenIds in market: {list(markets[0].keys())}")
                else:
                    print(f"  No markets found")
            else:
                print(f"  Markets fetch failed: {markets_res.status_code}")
        except Exception as e:
            print(f"  ERROR: {e}")


async def test_render_backend():
    """Test: Is the Render backend responding?"""
    print("\n=== TEST 6: Render Backend Health ===")
    async with httpx.AsyncClient(timeout=15.0) as client:
        for endpoint in ["/health", "/api/stats", "/api/wallets"]:
            try:
                res = await client.get(f"{RENDER_BACKEND}{endpoint}")
                print(f"  {endpoint}: {res.status_code} -> {res.text[:200]}")
            except Exception as e:
                print(f"  {endpoint}: ERROR: {e}")


async def test_neon_db():
    """Test: Can we connect to Neon and query tables?"""
    print("\n=== TEST 7: Neon Database ===")
    try:
        from app.database import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Check tables exist
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = [r[0] for r in result.fetchall()]
            print(f"  Tables: {tables}")
            
            # Count rows in each
            for table in tables:
                count = (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
                print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  ERROR: {e}")


async def main():
    print("=" * 60)
    print("BALEEN INTEGRATION TESTS")
    print("=" * 60)
    
    await test_polymarket_leaderboard()
    await test_polymarket_trades()
    await test_polymarket_wallet_trades()
    await test_gamma_markets()
    await test_clob_orderbook()
    await test_render_backend()
    await test_neon_db()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
