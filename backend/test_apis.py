# -*- coding: utf-8 -*-
"""
Baleen API Smoke Tests - Tests all external APIs that the system depends on.
"""
import asyncio
import httpx
import json
import time
import sys
import os

# Fix Windows encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

results = []

def log_pass(name, detail=""):
    results.append(("PASS", name))
    msg = f"  [PASS]  {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)

def log_fail(name, detail=""):
    results.append(("FAIL", name))
    msg = f"  [FAIL]  {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)

def log_warn(name, detail=""):
    results.append(("WARN", name))
    msg = f"  [WARN]  {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


async def test_polymarket_data_api():
    """Test 1: Polymarket Data API - GET /trades"""
    print("\n[1/6] Polymarket Data API - /trades")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get("https://data-api.polymarket.com/trades", params={"limit": 5})
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    trade = data[0]
                    keys = list(trade.keys())
                    log_pass(f"Returned {len(data)} trades", f"Keys: {keys[:8]}")
                    print(f"         Sample trade: {json.dumps(trade, indent=2, default=str)[:500]}")
                    return data
                else:
                    log_fail("Response is empty or not a list")
            else:
                log_fail(f"HTTP {resp.status_code}", resp.text[:200])
        except httpx.ConnectError as e:
            log_fail(f"Cannot connect to data-api.polymarket.com", str(e)[:100])
        except Exception as e:
            log_fail(f"Error: {type(e).__name__}", str(e)[:100])
    return None


async def test_polymarket_leaderboard():
    """Test 2: Polymarket Leaderboard API"""
    print("\n[2/6] Polymarket Leaderboard API")
    async with httpx.AsyncClient(timeout=15.0) as client:
        urls_to_try = [
            ("https://data-api.polymarket.com/leaderboard", {"limit": 5, "window": "all"}),
            ("https://data-api.polymarket.com/v1/leaderboard", {"limit": 5, "window": "all"}),
            ("https://gamma-api.polymarket.com/leaderboard", {"limit": 5}),
        ]
        for url, params in urls_to_try:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        entry = data[0]
                        log_pass(f"URL: {url} -- returned {len(data)} entries")
                        print(f"         Sample entry: {json.dumps(entry, indent=2, default=str)[:500]}")
                        return data
                    elif isinstance(data, dict):
                        log_pass(f"URL: {url} -- returned dict response")
                        print(f"         Response keys: {list(data.keys())[:10]}")
                        print(f"         Sample: {json.dumps(data, indent=2, default=str)[:500]}")
                        return data
                    else:
                        log_warn(f"URL: {url} -- returned empty data")
                else:
                    log_warn(f"URL: {url} -- HTTP {resp.status_code}")
            except httpx.ConnectError:
                log_warn(f"URL: {url} -- cannot connect")
            except Exception as e:
                log_warn(f"URL: {url} -- {type(e).__name__}: {str(e)[:80]}")

        log_fail("No leaderboard endpoint returned data")
    return None


async def test_polymarket_clob():
    """Test 3: Polymarket CLOB API - order book"""
    print("\n[3/6] Polymarket CLOB API - /book")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Get a valid market first
            markets_resp = await client.get("https://gamma-api.polymarket.com/markets", params={"limit": 3, "active": "true", "closed": "false"})
            if markets_resp.status_code == 200:
                markets = markets_resp.json()
                if isinstance(markets, list) and len(markets) > 0:
                    market = markets[0]
                    question = market.get("question", market.get("title", "unknown"))
                    print(f"         Found market: {question[:80]}")

                    # Extract token_id
                    token_id = None
                    clob_token_ids = market.get("clobTokenIds")
                    if clob_token_ids:
                        if isinstance(clob_token_ids, str):
                            try:
                                parsed = json.loads(clob_token_ids)
                                token_id = parsed[0] if isinstance(parsed, list) else clob_token_ids
                            except json.JSONDecodeError:
                                token_id = clob_token_ids
                        elif isinstance(clob_token_ids, list) and len(clob_token_ids) > 0:
                            token_id = clob_token_ids[0]

                    if not token_id:
                        tokens = market.get("tokens", [])
                        if tokens and len(tokens) > 0:
                            token_id = tokens[0].get("token_id")

                    if token_id:
                        book_resp = await client.get("https://clob.polymarket.com/book", params={"token_id": token_id})
                        if book_resp.status_code == 200:
                            book = book_resp.json()
                            bids = book.get("bids", [])
                            asks = book.get("asks", [])
                            log_pass(f"Order book: {len(bids)} bids, {len(asks)} asks")
                            if bids:
                                print(f"         Best bid: {bids[0]}")
                            if asks:
                                print(f"         Best ask: {asks[0]}")
                            return book
                        else:
                            log_fail(f"CLOB /book HTTP {book_resp.status_code}", book_resp.text[:200])
                    else:
                        log_warn("Could not extract token_id from market")
                        print(f"         Market fields: {list(market.keys())[:12]}")
                else:
                    log_fail("No markets returned from Gamma API")
            else:
                log_fail(f"Gamma /markets HTTP {markets_resp.status_code}")
        except httpx.ConnectError:
            log_fail("Cannot connect to gamma-api.polymarket.com or clob.polymarket.com")
        except Exception as e:
            log_fail(f"{type(e).__name__}: {str(e)[:100]}")
    return None


async def test_groq_api():
    """Test 4: Groq AI API - LLM summary generation"""
    print("\n[4/6] Groq AI API - LLM Summary")

    keys = [
        os.environ.get("GROQ_API_KEY_1", ""),
        os.environ.get("GROQ_API_KEY_2", ""),
        os.environ.get("GROQ_API_KEY_3", ""),
    ]

    prompt = """You are describing a Polymarket trader's style for a retail audience.
Use ONLY the numbers provided. 2-3 sentences, no jargon.
Stats: Win rate: 88%, Total PnL: $120,000, Avg trades/day: 3.2, Max drawdown: 7%
Also output a 2-4 word style tag."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, key in enumerate(keys):
            try:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 200,
                        "temperature": 0.3,
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    log_pass(f"Key {i+1} works -- model: llama-3.3-70b-versatile")
                    print(f"         AI Response: {content[:300]}")
                    return content
                else:
                    log_warn(f"Key {i+1} -- HTTP {resp.status_code}: {resp.text[:100]}")
            except httpx.ConnectError:
                log_warn(f"Key {i+1} -- cannot connect to api.groq.com")
            except Exception as e:
                log_warn(f"Key {i+1} -- {type(e).__name__}: {str(e)[:80]}")

        log_fail("All 3 Groq API keys failed")
    return None


async def test_envio_hypersync():
    """Test 5: Envio HyperSync - Polygon connection"""
    print("\n[5/6] Envio HyperSync - Polygon Connection")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Test the height endpoint
        try:
            resp = await client.get(
                "https://polygon.hypersync.xyz/height",
                headers={"Authorization": "Bearer 2e5371c8-5c65-4996-8f7b-d25b0f40c585"},
            )
            if resp.status_code == 200:
                try:
                    height = resp.json()
                except Exception:
                    height = resp.text.strip()
                log_pass(f"Polygon block height: {height}")
                return height
            else:
                log_fail(f"Height endpoint HTTP {resp.status_code}")
        except httpx.ConnectError:
            log_fail("Cannot connect to polygon.hypersync.xyz")
        except Exception as e:
            log_fail(f"{type(e).__name__}: {str(e)[:100]}")
    return None


async def test_gamma_markets():
    """Test 6: Gamma API - market metadata"""
    print("\n[6/6] Gamma API - Market Metadata")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get("https://gamma-api.polymarket.com/markets", params={"limit": 3, "active": "true"})
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    market = data[0]
                    question = market.get("question", market.get("title", "N/A"))
                    log_pass(f"Returned {len(data)} markets")
                    print(f"         Market: \"{question[:80]}\"")
                    print(f"         Available fields: {list(market.keys())[:12]}")
                    return data
                else:
                    log_fail("No markets returned")
            else:
                log_fail(f"HTTP {resp.status_code}")
        except httpx.ConnectError:
            log_fail("Cannot connect to gamma-api.polymarket.com")
        except Exception as e:
            log_fail(f"{type(e).__name__}: {str(e)[:100]}")
    return None


async def main():
    print("")
    print("=" * 60)
    print("  BALEEN - External API Smoke Tests")
    print("=" * 60)

    start = time.time()

    await test_polymarket_data_api()
    await test_polymarket_leaderboard()
    await test_polymarket_clob()
    await test_groq_api()
    await test_envio_hypersync()
    await test_gamma_markets()

    elapsed = time.time() - start

    print("")
    print("=" * 60)
    passes = sum(1 for r in results if r[0] == "PASS")
    fails = sum(1 for r in results if r[0] == "FAIL")
    warns = sum(1 for r in results if r[0] == "WARN")

    print(f"  {passes} passed  {warns} warnings  {fails} failed  ({elapsed:.1f}s)")

    if fails > 0:
        print(f"\n  Failed tests:")
        for status, name in results:
            if status == "FAIL":
                print(f"    x {name}")

    print("=" * 60)
    print("")

    return 1 if fails > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
