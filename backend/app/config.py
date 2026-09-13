import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
default_db_path = (project_root / "baleen.db").as_posix()

class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite+aiosqlite:///{default_db_path}"
    GROQ_API_KEY_1: str = ""
    GROQ_API_KEY_2: str = ""
    GROQ_API_KEY_3: str = ""
    ENVIO_API_KEY: str = ""
    POLYMARKET_DATA_API_URL: str = "https://data-api.polymarket.com"
    CLOB_API_URL: str = "https://clob.polymarket.com"
    GAMMA_API_URL: str = "https://gamma-api.polymarket.com"
    POLYMARKET_MIN_ORDER_USD: float = 1.0
    BACKEND_URL: str = "http://localhost:8000"
    NETTED_LEDGER_ENABLED: bool = True
    NETTED_LEDGER_EXPIRY_HOURS: float = 4.0
    NETTED_LEDGER_EXPIRY_BEHAVIOR: str = "flush"  # "flush" or "drop"
    NETTED_LEDGER_MIN_THRESHOLD_USD: float = 1.0
    AUTH_SECRET: str = "baleen_default_secure_auth_secret_must_change_in_prod"
    ADMIN_API_KEY: str = ""
    LISTENER_SERVICE_KEY: str = ""
    LIVE_EXECUTION_ENABLED: bool = False
    POLYGON_SETTLEMENT_RPC_URL: str = ""
    POLYMARKET_BUILDER_API_KEY: str = ""
    POLYMARKET_BUILDER_SECRET: str = ""
    POLYMARKET_BUILDER_PASSPHRASE: str = ""
    RUN_BACKGROUND_WORKERS: bool = True
    ALLOW_DESTRUCTIVE_ADMIN_WIPE: bool = False
    ENVIRONMENT: str = "development"
    SETTINGS_ENCRYPTION_KEY: str = ""
    SETTINGS_ENCRYPTION_KEY_PREVIOUS: str = ""

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        # Convert standard Postgres URL prefixes to asyncpg driver
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg doesn't understand sslmode=require; convert to ssl=require
        if "sslmode=require" in url:
            url = url.replace("sslmode=require", "ssl=require")
        return url

    @model_validator(mode="after")
    def validate_production_security(self):
        env = (self.ENVIRONMENT or "").lower()
        is_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))
        is_render = bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL"))

        if (is_railway or is_render) and env != "production":
            raise ValueError(
                "Deployment detected on Railway/Render: ENVIRONMENT must be explicitly set to 'production'."
            )

        if env == "production":
            if os.environ.get("TESTING") == "1":
                raise ValueError("TESTING mode is strictly prohibited in deployed production.")
            if not self.AUTH_SECRET or self.AUTH_SECRET == "baleen_default_secure_auth_secret_must_change_in_prod":
                raise ValueError("AUTH_SECRET must be explicitly set to a custom strong secret in production.")
            if not self.ADMIN_API_KEY:
                raise ValueError("ADMIN_API_KEY must be explicitly set in production.")
            if not self.LISTENER_SERVICE_KEY:
                raise ValueError("LISTENER_SERVICE_KEY must be explicitly set in production.")
            if not self.SETTINGS_ENCRYPTION_KEY:
                raise ValueError("SETTINGS_ENCRYPTION_KEY must be explicitly set in production.")
            if self.SETTINGS_ENCRYPTION_KEY == self.AUTH_SECRET:
                raise ValueError("SETTINGS_ENCRYPTION_KEY must be distinct from AUTH_SECRET (separate signing and encryption keys).")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("Production deployment requires PostgreSQL DATABASE_URL. SQLite is not allowed.")
        return self

    model_config = SettingsConfigDict(
        env_file=os.path.join(Path(__file__).parent.parent.parent, ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
