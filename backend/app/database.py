from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe idempotent migrations for Postgres/SQLite
        new_cols = [
            ("wallets", "is_hft", "BOOLEAN DEFAULT FALSE"),
            ("wallets", "trades_per_hour", "FLOAT"),
            ("wallets", "wilson_lb", "FLOAT"),
            ("wallets", "alpha_per_trade", "FLOAT"),
            ("wallets", "profit_factor", "FLOAT"),
            ("wallets", "first_trade_at", "TIMESTAMP"),
            ("wallets", "last_trade_at", "TIMESTAMP"),
            ("wallets", "cached_daily_pnl", "TEXT"),
        ]
        from sqlalchemy import text
        for table, col, col_type in new_cols:
            try:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type};"))
            except Exception:
                pass
