from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "Life Reflex Arc"
    debug: bool = False

    # Database – defaults to SQLite for zero-config local dev
    # For production set: postgresql+asyncpg://user:pass@host/db
    database_url: str = "sqlite+aiosqlite:///./lifereflexarc.db"

    # Redis – leave empty to use the built-in in-memory fallback
    redis_url: Optional[str] = None

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # SOS countdown seconds
    sos_duration_sec: int = 10

    # CORS origins (comma-separated)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
