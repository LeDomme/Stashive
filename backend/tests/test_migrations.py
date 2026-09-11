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
LOCATION_TABLES = {"locations"}


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


def test_location_tree_migration_preserves_t04_data_and_reverses_cleanly(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'location-tree-migration-test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = migration_config(database_url)

    try:
        command.upgrade(config, "0003_collections_acl")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (username, password_hash, is_instance_admin, is_active) "
                    "VALUES ('owner', 'hash', 0, 1)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO collections (owner_user_id, name, type) "
                    "VALUES (1, 'Films', 'movies')"
                )
            )
        engine.dispose()

        command.upgrade(config, "head")
        inspector = inspect(create_engine(database_url))
        assert LOCATION_TABLES.issubset(inspector.get_table_names())
        location_foreign_keys = {
            foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("locations")
        }
        assert location_foreign_keys == {
            "collections",
            "locations",
        }
        assert {index["name"] for index in inspector.get_indexes("locations")} == {
            "ix_locations_collection_id",
            "ix_locations_parent_id",
        }
        with create_engine(database_url).connect() as connection:
            assert connection.scalar(text("SELECT name FROM collections")) == "Films"

        command.downgrade(config, "0003_collections_acl")
        inspector = inspect(create_engine(database_url))
        assert LOCATION_TABLES.isdisjoint(inspector.get_table_names())
        with create_engine(database_url).connect() as connection:
            assert connection.scalar(text("SELECT name FROM collections")) == "Films"

        command.upgrade(config, "head")
        assert LOCATION_TABLES.issubset(inspect(create_engine(database_url)).get_table_names())
    finally:
        get_settings.cache_clear()


def test_inventory_location_migration_preserves_items_and_reverses_cleanly(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'inventory-location-migration-test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = migration_config(database_url)

    try:
        command.upgrade(config, "0004_location_tree")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO collections (name, type) VALUES ('Films', 'movies')")
            )
            connection.execute(
                text(
                    "INSERT INTO catalog_entries (collection_id, display_title, type) "
                    "VALUES (1, 'Alien', 'movie')"
                )
            )
            connection.execute(
                text("INSERT INTO editions (catalog_entry_id, display_name) VALUES (1, 'Blu-ray')")
            )
            connection.execute(text("INSERT INTO inventory_items (edition_id) VALUES (1)"))
        engine.dispose()

        command.upgrade(config, "head")
        inspector = inspect(create_engine(database_url))
        location_column = next(
            column
            for column in inspector.get_columns("inventory_items")
            if column["name"] == "location_id"
        )
        assert location_column["nullable"] is True
        assert {
            foreign_key["referred_table"]
            for foreign_key in inspector.get_foreign_keys("inventory_items")
        } == {
            "editions",
            "locations",
        }
        assert {index["name"] for index in inspector.get_indexes("inventory_items")} == {
            "ix_inventory_items_edition_id",
            "ix_inventory_items_location_id",
        }
        with create_engine(database_url).connect() as connection:
            assert connection.scalar(text("SELECT location_id FROM inventory_items")) is None

        command.downgrade(config, "0004_location_tree")
        assert "location_id" not in {
            column["name"]
            for column in inspect(create_engine(database_url)).get_columns("inventory_items")
        }
        command.upgrade(config, "head")
        assert "location_id" in {
            column["name"]
            for column in inspect(create_engine(database_url)).get_columns("inventory_items")
        }
    finally:
        get_settings.cache_clear()


def test_edition_media_format_migration_reverses_cleanly(monkeypatch, tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'edition-format.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = migration_config(database_url)
    command.upgrade(config, "0005_inventory_location")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO collections (name, type) VALUES ('Films', 'movies')"))
        connection.execute(text("INSERT INTO catalog_entries (collection_id, display_title, type) VALUES (1, 'Alien', 'movie')"))  # noqa: E501
        connection.execute(text("INSERT INTO editions (catalog_entry_id, display_name) VALUES (1, 'Blu-ray')"))  # noqa: E501
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT media_format FROM editions")) is None
    command.downgrade(config, "0005_inventory_location")
    assert "media_format" not in {column["name"] for column in inspect(engine).get_columns("editions")}  # noqa: E501
    command.upgrade(config, "head")
    assert "media_format" in {column["name"] for column in inspect(engine).get_columns("editions")}
