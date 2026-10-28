from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me-to-a-long-random-string"
    jwt_expire_minutes: int = 1440
    database_url: str = "sqlite:///./astratrade.db"
    cors_origins: str = "http://localhost:3000"
    admin_email: str = "admin@example.com"
    admin_password: str = "admin12345"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize a hosting provider's DATABASE_URL (Render/Railway/Heroku-style
        `postgres://` or bare `postgresql://`) to the psycopg3 driver SQLAlchemy dialect
        this project installs (`psycopg[binary]`), so a pasted-in Postgres URL just works."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
