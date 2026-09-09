"""Persistence tests for the generic title, edition, and copy model."""

from collections.abc import Callable

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.db.database import Database
from app.db.models import CatalogEntry, Collection, Edition, Identifier, InventoryItem


def test_title_edition_and_copy_hierarchy_supports_multiple_children(database: Database) -> None:
    with database.session_factory() as session:
        collection = Collection(name="Films", type="movies")
        entry = CatalogEntry(display_title="Alien", type="movie")
        blu_ray = Edition(display_name="German Blu-ray")
        uhd = Edition(display_name="German UHD")
        blu_ray.identifiers.append(Identifier(type="ean", value="1234567890123", source="manual"))
        blu_ray.inventory_items.extend(
            [
                InventoryItem(condition="good"),
                InventoryItem(notes="Second copy"),
            ]
        )
        entry.editions.extend([blu_ray, uhd])
        collection.catalog_entries.append(entry)
        session.add(collection)
        session.commit()

        persisted_entry = session.scalar(select(CatalogEntry).where(CatalogEntry.id == entry.id))
        assert persisted_entry is not None
        assert persisted_entry.collection_id == collection.id
        assert [edition.display_name for edition in persisted_entry.editions] == [
            "German Blu-ray",
            "German UHD",
        ]
        assert len(blu_ray.inventory_items) == 2
        assert blu_ray.identifiers[0].edition_id == blu_ray.id


@pytest.mark.parametrize(
    ("factory", "expected_table"),
    [
        (
            lambda: CatalogEntry(collection_id=999, display_title="Unknown", type="movie"),
            "catalog_entries",
        ),
        (
            lambda: Edition(catalog_entry_id=999, display_name="Unknown"),
            "editions",
        ),
        (
            lambda: Identifier(edition_id=999, type="ean", value="123"),
            "identifiers",
        ),
        (
            lambda: InventoryItem(edition_id=999),
            "inventory_items",
        ),
    ],
)
def test_invalid_foreign_keys_are_rejected(
    database: Database,
    factory: Callable[[], CatalogEntry | Edition | Identifier | InventoryItem],
    expected_table: str,
) -> None:
    with database.session_factory() as session:
        session.add(factory())

        with pytest.raises(IntegrityError, match=expected_table):
            session.commit()


def test_identifier_values_are_not_globally_unique(database: Database) -> None:
    with database.session_factory() as session:
        collection = Collection(name="Films", type="movies")
        entry = CatalogEntry(display_title="Alien", type="movie")
        first_edition = Edition(display_name="Blu-ray")
        second_edition = Edition(display_name="UHD")
        first_edition.identifiers.append(Identifier(type="ean", value="1234567890123"))
        second_edition.identifiers.append(Identifier(type="ean", value="1234567890123"))
        entry.editions.extend([first_edition, second_edition])
        collection.catalog_entries.append(entry)
        session.add(collection)
        session.commit()

        identifier_count = session.scalar(select(func.count()).select_from(Identifier))
        assert identifier_count == 2


def test_collection_delete_cascades_to_the_owned_inventory_hierarchy(database: Database) -> None:
    with database.session_factory() as session:
        collection = Collection(name="Films", type="movies")
        entry = CatalogEntry(display_title="Alien", type="movie")
        edition = Edition(display_name="Blu-ray")
        edition.identifiers.append(Identifier(type="ean", value="1234567890123"))
        edition.inventory_items.append(InventoryItem())
        entry.editions.append(edition)
        collection.catalog_entries.append(entry)
        session.add(collection)
        session.commit()

        session.execute(delete(Collection).where(Collection.id == collection.id))
        session.commit()

        assert session.scalar(select(func.count()).select_from(CatalogEntry)) == 0
        assert session.scalar(select(func.count()).select_from(Edition)) == 0
        assert session.scalar(select(func.count()).select_from(Identifier)) == 0
        assert session.scalar(select(func.count()).select_from(InventoryItem)) == 0
