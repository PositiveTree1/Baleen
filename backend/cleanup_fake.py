import asyncio
from sqlalchemy import text
from app.database import engine

async def cleanup():
    async with engine.begin() as conn:
        # Delete the fake seed wallets
        result = await conn.execute(text(
            "DELETE FROM wallets WHERE address IN ("
            "'0x192e22ed335d288d4050dca7807604586cc93e1b',"
            "'0x82f9d50a2abf5fc67d8cd0dfdf0271d4715fba33',"
            "'0x8a1dbfb62660d5b4e7ec9df3424177dd71439226'"
            ")"
        ))
        print(f"Deleted {result.rowcount} fake wallets")
        
        # Show remaining
        remaining = await conn.execute(text("SELECT address, status FROM wallets"))
        rows = remaining.fetchall()
        print(f"Remaining wallets: {len(rows)}")
        for r in rows:
            print(f"  {r}")

if __name__ == "__main__":
    asyncio.run(cleanup())
