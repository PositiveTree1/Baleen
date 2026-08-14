import asyncio
import httpx
from datetime import datetime

async def test():
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 0x8dxd $2.21M whale
        addr = "0x63ce342161250d705dc0b16df89036c8e5f9ba9a"
        url = "https://data-api.polymarket.com/trades"
        res = await client.get(url, params={"user": addr, "limit": 100})
        print(f"Status: {res.status_code}")
        trades = res.json()
        if isinstance(trades, list) and trades:
            print(f"Fetched {len(trades)} trades for {addr}")
            print(f"Sample trade: {trades[0]}")
            ts_list = [t.get("timestamp") for t in trades if t.get("timestamp")]
            if ts_list:
                min_dt = datetime.fromtimestamp(min(ts_list) / 1000 if min(ts_list) > 1e11 else min(ts_list))
                max_dt = datetime.fromtimestamp(max(ts_list) / 1000 if max(ts_list) > 1e11 else max(ts_list))
                print(f"Date range of sample: {min_dt} -> {max_dt}")

asyncio.run(test())
