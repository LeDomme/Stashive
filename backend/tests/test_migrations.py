"""Migration lifecycle tests for the database core schema."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from app.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]

CORE_TABLES = {
    "collections",
    "catalog_entries",
    "editions",
    "identifiers",
    "inventory_items",
}


def migration_config(database_url: str) -> Config:
    """Return an Alembic configuration targeting an isolated test database."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_database_core_migration_upgrades_downgrades_and_upgrades_again(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration-test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = migration_config(database_url)

    try:
        command.upgrade(config, "head")
        assert CORE_TABLES.issubset(inspect(create_engine(database_url)).get_table_names())

        command.downgrade(config, "base")
        assert CORE_TABLES.isdisjoint(inspect(create_engine(database_url)).get_table_names())

        command.upgrade(config, "head")
        assert CORE_TABLES.issubset(inspect(create_engine(database_url)).get_table_names())
    finally:
        get_settings.cache_clear()
