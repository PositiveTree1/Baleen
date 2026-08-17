import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import settings

logger = logging.getLogger(__name__)

# Determine active database URL with fallback handling
db_url = settings.async_database_url

# If running with SQLite, ensure WAL mode is enabled
engine_kwargs = {"echo": False, "future": True}
if "sqlite" in db_url:
    if os.path.exists("/data") and "sqlite+aiosqlite:///./baleen.db" in db_url:
        db_url = "sqlite+aiosqlite:////data/baleen.db"
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL settings: pre-ping to detect stale connections and keep pools lean
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_recycle"] = 300

try:
    engine = create_async_engine(db_url, **engine_kwargs)
except Exception as e:
    logger.warning(f"Failed to create engine with {db_url}: {e}. Falling back to SQLite.")
    fallback_url = "sqlite+aiosqlite:////data/baleen.db" if os.path.exists("/data") else "sqlite+aiosqlite:///./baleen.db"
    engine = create_async_engine(fallback_url, echo=False, future=True, connect_args={"check_same_thread": False})

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
AsyncSessionLocal = SessionLocal

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session

NEW_COLS = [
    ("wallets", "is_hft", "BOOLEAN DEFAULT FALSE"),
    ("wallets", "trades_per_hour", "FLOAT"),
    ("wallets", "wilson_lb", "FLOAT"),
    ("wallets", "alpha_per_trade", "FLOAT"),
    ("wallets", "profit_factor", "FLOAT"),
    ("wallets", "first_trade_at", "TIMESTAMP"),
    ("wallets", "last_trade_at", "TIMESTAMP"),
    ("wallets", "cached_daily_pnl", "TEXT"),
]

async def init_db():
    global engine, SessionLocal, AsyncSessionLocal
    try:
        async with engine.begin() as conn:
            # Enable WAL mode if SQLite
            if "sqlite" in str(engine.url):
                await conn.execute(text("PRAGMA journal_mode=WAL;"))
                await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            await conn.run_sync(Base.metadata.create_all)
            
            # Safe idempotent migrations for Postgres/SQLite
            for table, col, col_type in NEW_COLS:
                try:
                    if "sqlite" in str(conn.engine.url):
                        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                    else:
                        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type};"))
                except Exception:
                    pass
        logger.info(f"Database initialized successfully ({engine.url.drivername}).")
    except Exception as exc:
        logger.error(f"Error initializing primary database ({engine.url.drivername}): {exc}. Activating SQLite fallback...")
        fallback_url = "sqlite+aiosqlite:////data/baleen.db" if os.path.exists("/data") else "sqlite+aiosqlite:///./baleen.db"
        engine = create_async_engine(fallback_url, echo=False, future=True, connect_args={"check_same_thread": False})
        SessionLocal.configure(bind=engine)
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            await conn.run_sync(Base.metadata.create_all)
            for table, col, col_type in NEW_COLS:
                try:
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                except Exception:
                    pass
        logger.info(f"SQLite fallback database initialized at {fallback_url}.")
