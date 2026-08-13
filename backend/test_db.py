import asyncio
from app.database import engine

async def test_conn():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("DB connection successful!")
    except Exception as e:
        print(f"DB connection failed: {e}")

if __name__ == "__main__":
    from sqlalchemy import text
    asyncio.run(test_conn())
