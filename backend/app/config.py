import os
from pydantic_settings import BaseSettings, SettingsConfigDict
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
    POLYMARKET_MIN_ORDER_USD: float = 5.0
    BACKEND_URL: str = "http://localhost:8000"

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

    model_config = SettingsConfigDict(
        env_file=os.path.join(Path(__file__).parent.parent.parent, ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
