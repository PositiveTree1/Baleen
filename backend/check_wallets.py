import asyncio
from sqlalchemy import text
from app.database import engine

async def check():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT address, all_time_pnl_usd, win_rate_pct FROM wallets"))
        print(res.fetchall())

if __name__ == "__main__":
    asyncio.run(check())
