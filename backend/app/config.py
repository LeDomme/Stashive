"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for the Stashive backend."""

    database_url: str = "sqlite:///./data/stashive.db"
    sqlite_busy_timeout_ms: int = 5_000
    app_environment: str = "development"
    auth_session_cookie_name: str = "stashive_session"
    auth_csrf_cookie_name: str = "stashive_csrf"
    auth_cookie_secure: bool = False
    auth_session_lifetime_hours: int = 168
    auth_setup_token_lifetime_minutes: int = 60
    auth_test_setup_token: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable application settings."""
    return Settings()
