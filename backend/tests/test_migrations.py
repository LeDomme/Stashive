"""Migration lifecycle tests for the database core schema."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

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

ACL_TABLES = {"collection_members"}


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


def test_collections_acl_migration_preserves_ownerless_legacy_collections(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'collections-acl-migration-test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = migration_config(database_url)

    try:
        command.upgrade(config, "0002_local_authentication")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO collections (name, type) VALUES ('Legacy', 'movies')")
            )
        engine.dispose()

        command.upgrade(config, "head")
        inspector = inspect(create_engine(database_url))
        assert ACL_TABLES.issubset(inspector.get_table_names())
        owner_column = next(
            column
            for column in inspector.get_columns("collections")
            if column["name"] == "owner_user_id"
        )
        assert owner_column["nullable"] is True
        assert {
            foreign_key["referred_table"]
            for foreign_key in inspector.get_foreign_keys("collections")
        } == {"users"}
        assert {
            foreign_key["referred_table"]
            for foreign_key in inspector.get_foreign_keys("collection_members")
        } == {
            "collections",
            "users",
        }
        with create_engine(database_url).connect() as connection:
            assert connection.scalar(text("SELECT owner_user_id FROM collections")) is None

        command.downgrade(config, "0002_local_authentication")
        inspector = inspect(create_engine(database_url))
        assert ACL_TABLES.isdisjoint(inspector.get_table_names())
        assert "owner_user_id" not in {
            column["name"] for column in inspector.get_columns("collections")
        }

        command.upgrade(config, "head")
        with create_engine(database_url).connect() as connection:
            assert connection.scalar(text("SELECT owner_user_id FROM collections")) is None
    finally:
        get_settings.cache_clear()
