import asyncio
import datetime
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import Wallet

async def seed_whales():
    async with SessionLocal() as db:
        whales = [
            Wallet(address="0x192e22ed335d288d4050dca7807604586cc93e1b", status="active", tier="A", win_rate_pct=0.65, all_time_pnl_usd=150000.0, avg_trades_per_day=5.2),
            Wallet(address="0x82f9d50a2abf5fc67d8cd0dfdf0271d4715fba33", status="active", tier="S", win_rate_pct=0.72, all_time_pnl_usd=450000.0, avg_trades_per_day=12.1),
            Wallet(address="0x8a1dbfb62660d5b4e7ec9df3424177dd71439226", status="active", tier="B", win_rate_pct=0.55, all_time_pnl_usd=75000.0, avg_trades_per_day=2.0)
        ]
        db.add_all(whales)
        await db.commit()
        print("Whales added!")

if __name__ == '__main__':
    asyncio.run(seed_whales())
