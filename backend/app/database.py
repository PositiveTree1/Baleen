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
    # PostgreSQL settings: background discovery, valuation and listener jobs
    # share this pool with interactive dashboard requests. Five connections was
    # not enough under a fresh discovery pass and made first-page loads wait
    # for the pool timeout. These values remain bounded and can be lowered by
    # the deployment environment when using a smaller provider plan.
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = int(os.environ.get("DATABASE_POOL_SIZE", "6"))
    engine_kwargs["max_overflow"] = int(os.environ.get("DATABASE_MAX_OVERFLOW", "8"))
    engine_kwargs["pool_recycle"] = 60
    engine_kwargs["pool_timeout"] = 10
    if not _using_sqlite_fallback:
        engine_kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0
        }

def redact_db_url(url: str) -> str:
    """Masks credentials in database URL for safe logging."""
    import re
    return re.sub(r':([^:@]+)@', ':****@', str(url))

def is_production_environment() -> bool:
    """Determines whether current deployment is in production mode."""
    return bool(
        os.environ.get("RENDER")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
        or getattr(settings, "ENVIRONMENT", "").lower() == "production"
    )

try:
    engine = create_async_engine(db_url, **engine_kwargs)
except Exception as e:
    _using_sqlite_fallback = True
    safe_url = redact_db_url(db_url)
    if is_production_environment():
        logger.critical(
            f"FATAL: Cannot connect to PostgreSQL ({safe_url}): {e}. "
            f"Set DATABASE_URL in environment variables to your Supabase connection string. "
            f"Refusing to fall back to ephemeral SQLite in production."
        )
        raise RuntimeError(
            f"PostgreSQL connection failed and SQLite fallback is disabled in production. "
            f"Set the DATABASE_URL environment variable. Error: {e}"
        ) from e
    logger.warning(
        f"⚠️  Failed to create engine with {safe_url}: {e}. "
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

from app.migrations import run_versioned_migrations, get_schema_version

async def init_db():
    global engine, SessionLocal, AsyncSessionLocal, _using_sqlite_fallback
    
    # Retry loop to handle Render/Railway rolling container deployments where PgBouncer slots drain
    max_retries = 5
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                is_postgres = "postgres" in str(conn.engine.url)
                if is_postgres:
                    # Serialize DDL and migration runners across all replicas
                    await conn.execute(text("SELECT pg_advisory_xact_lock(20260908, 1);"))
                elif "sqlite" in str(engine.url):
                    await conn.execute(text("PRAGMA journal_mode=WAL;"))
                    await conn.execute(text("PRAGMA synchronous=NORMAL;"))
                await conn.run_sync(Base.metadata.create_all)
                
                # Run versioned migrations (replaces ad-hoc column ALTER loops)
                schema_ver = await run_versioned_migrations(conn)

            db_driver = engine.url.drivername
            is_postgres = "postgres" in db_driver
            if is_postgres:
                logger.info(f"✅ Database initialized successfully — connected to Supabase PostgreSQL ({db_driver}), schema v{schema_ver}.")
            else:
                logger.warning(
                    f"⚠️  Database initialized with LOCAL SQLite ({db_driver}), schema v{schema_ver}. "
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
    if is_production_environment():
        logger.critical(
            f"FATAL: PostgreSQL initialization failed after {max_retries} retries: {exc}. "
            f"Check your DATABASE_URL environment variable."
        )
        raise RuntimeError(
            f"PostgreSQL initialization failed in production after {max_retries} retries. "
            f"Fix DATABASE_URL in environment variables. Error: {exc}"
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
        schema_ver = await run_versioned_migrations(conn)
    logger.warning(
        f"⚠️  SQLite fallback database initialized at {fallback_url}, schema v{schema_ver}. "
        f"Data will NOT persist across deploys/restarts!"
    )
