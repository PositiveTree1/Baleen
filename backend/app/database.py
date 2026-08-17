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

    # Auto-seed initial 6 VIP Alpha Whales if empty
    try:
        from app.models import Wallet
        from sqlalchemy import select, func
        async with SessionLocal() as db:
            cnt = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "active"))).scalar() or 0
            if cnt == 0:
                vip_wallets = [
                    Wallet(
                        address="0x63ce3421c640a44e59feedb93f18e97a3cf53549",
                        status="active",
                        tier="gold_sniper",
                        all_time_pnl_usd=2210000.0,
                        win_rate_pct=79.2,
                        baleen_score=98.0,
                        ai_style_tag="Mega Whale",
                        ai_summary="Titan VIP: High-notional institutional market leader with $2.2M+ lifetime PnL.",
                        avg_trades_per_day=6.5,
                        trades_per_hour=0.8,
                        wilson_lb=74.0,
                        alpha_per_trade=450.0,
                        profit_factor=4.2
                    ),
                    Wallet(
                        address="0x6d9fc316fcb1e1fb33c2a6ae1d2cfcfc7cbabfa1",
                        status="active",
                        tier="gold_sniper",
                        all_time_pnl_usd=299000.0,
                        win_rate_pct=84.5,
                        baleen_score=95.0,
                        ai_style_tag="Macro Whale",
                        ai_summary="Titan VIP: Systematic macro & geopolitical resolution sniper with strong historical alpha.",
                        avg_trades_per_day=4.2,
                        trades_per_hour=0.4,
                        wilson_lb=78.0,
                        alpha_per_trade=310.0,
                        profit_factor=3.8
                    ),
                    Wallet(
                        address="0xdf17f4a86b3cc76ab943c3328eb9f8c6ebf242c7",
                        status="active",
                        tier="gold_sniper",
                        all_time_pnl_usd=340000.0,
                        win_rate_pct=82.1,
                        baleen_score=94.0,
                        ai_style_tag="Alpha Whale",
                        ai_summary="Titan VIP: Clear-Corridor - Deep liquidity political & cultural market specialist.",
                        avg_trades_per_day=5.1,
                        trades_per_hour=0.5,
                        wilson_lb=76.0,
                        alpha_per_trade=280.0,
                        profit_factor=3.9
                    ),
                    Wallet(
                        address="0x1cc16713915be5cfef36cb1e85f09623e110ec43",
                        status="active",
                        tier="gold_sniper",
                        all_time_pnl_usd=185000.0,
                        win_rate_pct=88.0,
                        baleen_score=92.0,
                        ai_style_tag="Sniper Whale",
                        ai_summary="Titan VIP: Wickier - High precision tactical event trader with 88% win rate.",
                        avg_trades_per_day=3.8,
                        trades_per_hour=0.3,
                        wilson_lb=81.0,
                        alpha_per_trade=220.0,
                        profit_factor=3.5
                    ),
                    Wallet(
                        address="0x614dc8d37a5be5530df5eb42bf0082b43b679b84",
                        status="active",
                        tier="standard",
                        all_time_pnl_usd=142000.0,
                        win_rate_pct=76.4,
                        baleen_score=86.0,
                        ai_style_tag="Volume Whale",
                        ai_summary="Titan VIP: mr.ozi - Consistent high-volume probability trader.",
                        avg_trades_per_day=7.2,
                        trades_per_hour=0.9,
                        wilson_lb=71.0,
                        alpha_per_trade=150.0,
                        profit_factor=2.8
                    ),
                    Wallet(
                        address="0x7f9e2d1dd239272365e648434688970979a40879",
                        status="active",
                        tier="standard",
                        all_time_pnl_usd=115000.0,
                        win_rate_pct=74.8,
                        baleen_score=84.0,
                        ai_style_tag="Swing Whale",
                        ai_summary="Titan VIP: nojnn - Systematic swing trader across competitive binary contracts.",
                        avg_trades_per_day=4.9,
                        trades_per_hour=0.6,
                        wilson_lb=69.0,
                        alpha_per_trade=130.0,
                        profit_factor=2.5
                    ),
                ]
                db.add_all(vip_wallets)
                await db.commit()
                logger.info("Auto-seeded 6 VIP Alpha Whales in init_db.")
    except Exception as e:
        logger.debug(f"Auto-seed check note: {e}")
