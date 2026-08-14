import asyncio
from sqlalchemy import text
from app.database import engine

async def test():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT * FROM users"))
        print(res.fetchall())

if __name__ == '__main__':
    asyncio.run(test())
