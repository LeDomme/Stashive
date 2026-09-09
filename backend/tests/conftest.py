"""Shared fixtures for database-core tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.config import get_settings
from app.db.database import Database

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def migration_config(database_url: str) -> Config:
    """Return an Alembic configuration targeting an isolated test database."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Database]:
    """Upgrade and yield an isolated SQLite database for persistence tests."""
    database_url = f"sqlite:///{tmp_path / 'stashive-test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    command.upgrade(migration_config(database_url), "head")
    database = Database(database_url, sqlite_busy_timeout_ms=2_500)

    try:
        yield database
    finally:
        database.dispose()
        get_settings.cache_clear()
