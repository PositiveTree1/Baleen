import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import settings

logger = logging.getLogger(__name__)

# Determine active database URL with fallback handling
db_url = settings.async_database_url

# Track whether we're using the fallback so we can report it
_using_sqlite_fallback = False

# If running with SQLite, ensure WAL mode is enabled
engine_kwargs = {"echo": False, "future": True}
if "sqlite" in db_url:
    _using_sqlite_fallback = True
    if os.path.exists("/data") and "sqlite+aiosqlite:///./baleen.db" in db_url:
        db_url = "sqlite+aiosqlite:////data/baleen.db"
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL settings: pre-ping to detect stale connections and keep pools lean for Supabase pooler
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 2
    engine_kwargs["max_overflow"] = 3
    engine_kwargs["pool_recycle"] = 60
    engine_kwargs["pool_timeout"] = 15
    if not _using_sqlite_fallback:
        engine_kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0
        }

try:
    engine = create_async_engine(db_url, **engine_kwargs)
except Exception as e:
    _using_sqlite_fallback = True
    # On Render/production, refuse to silently degrade — crash loud so the deploy logs show the problem
    if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"):
        logger.critical(
            f"FATAL: Cannot connect to PostgreSQL ({db_url}): {e}. "
            f"Set DATABASE_URL in Render environment variables to your Supabase connection string. "
            f"Refusing to fall back to ephemeral SQLite in production."
        )
        raise RuntimeError(
            f"PostgreSQL connection failed and SQLite fallback is disabled in production. "
            f"Set the DATABASE_URL environment variable in Render. Error: {e}"
        ) from e
    logger.warning(
        f"⚠️  Failed to create engine with {db_url}: {e}. "
        f"Falling back to SQLite. Data will NOT persist across restarts!"
    )
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
    ("wallets", "pseudonym", "VARCHAR(255)"),
    ("wallets", "profile_image", "TEXT"),
    ("execution_logs", "event_slug", "VARCHAR(255)"),
    ("execution_logs", "icon", "TEXT"),
    ("execution_logs", "fee_usd", "FLOAT"),
    ("execution_logs", "market_category", "VARCHAR(100)"),
    ("execution_logs", "resolution_outcome", "VARCHAR(255)"),
    ("execution_logs", "realized_pnl_usd", "FLOAT"),
    ("execution_logs", "onchain_tx_hash", "VARCHAR(255)"),
    ("execution_logs", "onchain_log_index", "INTEGER"),
    ("live_wallet_links", "clob_api_secret_enc", "TEXT"),
    ("live_wallet_links", "clob_api_passphrase_enc", "TEXT"),
    ("live_wallet_links", "is_live_active", "BOOLEAN DEFAULT FALSE"),
    ("live_wallet_links", "live_balance_usdc", "FLOAT DEFAULT 0.0"),
    ("live_wallet_links", "last_verified_at", "TIMESTAMP"),
]

async def init_db():
    global engine, SessionLocal, AsyncSessionLocal, _using_sqlite_fallback
    
    # Retry loop to handle Render rolling container deployments where PgBouncer slots drain
    max_retries = 5
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
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

            db_driver = engine.url.drivername
            is_postgres = "postgres" in db_driver
            if is_postgres:
                logger.info(f"✅ Database initialized successfully — connected to Supabase PostgreSQL ({db_driver}).")
            else:
                logger.warning(
                    f"⚠️  Database initialized with LOCAL SQLite ({db_driver}). "
                    f"Data will NOT persist across deploys/restarts! "
                    f"Set DATABASE_URL to your Supabase PostgreSQL connection string."
                )
            return
        except Exception as exc:
            last_exception = exc
            logger.warning(f"Database connection attempt {attempt}/{max_retries} failed ({exc}). Retrying in 3s...")
            await asyncio.sleep(3)

    # If all retries failed
    exc = last_exception
    if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"):
        logger.critical(
            f"FATAL: PostgreSQL initialization failed after {max_retries} retries: {exc}. "
            f"Check your DATABASE_URL environment variable in Render settings."
        )
        raise RuntimeError(
            f"PostgreSQL initialization failed in production after {max_retries} retries. "
            f"Fix DATABASE_URL in Render environment variables. Error: {exc}"
        ) from exc

    logger.error(f"Error initializing primary database ({engine.url.drivername}): {exc}. Activating SQLite fallback...")
    _using_sqlite_fallback = True
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
    logger.warning(
        f"⚠️  SQLite fallback database initialized at {fallback_url}. "
        f"Data will NOT persist across deploys/restarts!"
    )
