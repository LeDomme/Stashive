"""Domain tests for the generic catalog, edition, identifier, and inventory core."""

from datetime import date

import pytest
from sqlalchemy import func, select

from app.db.database import Database
from app.db.models import CatalogEntry, Collection, Edition, Identifier, InventoryItem, Location
from app.inventory.service import (
    CatalogEntryNotFoundError,
    CrossCollectionLocationAssignmentError,
    DuplicateIdentifierError,
    InventoryService,
)
from app.locations.service import LocationHasInventoryItemsError, LocationHierarchyService


def add_collection(database: Database, name: str) -> int:
    """Persist a collection and return its identifier."""
    with database.session_factory() as session:
        collection = Collection(name=name, type="movies")
        session.add(collection)
        session.commit()
        return collection.id


def add_location(
    database: Database, collection_id: int, name: str, parent_id: int | None = None
) -> int:
    """Create a shelf location in the supplied collection."""
    with database.session_factory() as session:
        location = LocationHierarchyService().create_location(
            session,
            collection_id=collection_id,
            name=name,
            location_type="shelf",
            parent_id=parent_id,
        )
        return location.id


def add_edition(database: Database, collection_id: int, title: str = "Alien") -> int:
    """Create one generic title and one edition beneath it."""
    with database.session_factory() as session:
        service = InventoryService()
        entry = service.create_catalog_entry(
            session,
            collection_id=collection_id,
            display_title=title,
            entry_type="movie",
        )
        return service.create_edition(session, catalog_entry_id=entry.id, display_name="Blu-ray").id


def test_catalog_and_edition_crud_cascade_dependents(database: Database) -> None:
    collection_id = add_collection(database, "Films")
    with database.session_factory() as session:
        service = InventoryService()
        entry = service.create_catalog_entry(
            session,
            collection_id=collection_id,
            display_title="Alien",
            entry_type="movie",
            sort_title="Alien",
            notes="Classic",
        )
        updated_entry = service.update_catalog_entry(
            session,
            entry_id=entry.id,
            display_title="Alien (1979)",
            entry_type="movie",
            sort_title=None,
            notes=None,
        )
        edition = service.create_edition(
            session,
            catalog_entry_id=entry.id,
            display_name="German Blu-ray",
            release_date=date(2010, 1, 1),
            publisher="Fox",
            region="B",
            language="de",
        )
        second_edition = service.create_edition(
            session,
            catalog_entry_id=entry.id,
            display_name="German DVD",
        )
        second_entry = service.create_catalog_entry(
            session,
            collection_id=collection_id,
            display_title="Aliens",
            entry_type="movie",
        )
        updated_edition = service.update_edition(
            session,
            edition_id=edition.id,
            display_name="German UHD",
            release_date=None,
            publisher=None,
            region=None,
            language="de",
        )
        service.create_identifier(
            session,
            edition_id=edition.id,
            identifier_type="ean",
            value="123",
        )
        service.create_inventory_item(session, edition_id=edition.id)

        assert (updated_entry.display_title, updated_entry.sort_title, updated_entry.notes) == (
            "Alien (1979)",
            None,
            None,
        )
        assert (
            updated_edition.display_name,
            updated_edition.release_date,
            updated_edition.language,
        ) == (
            "German UHD",
            None,
            "de",
        )
        assert second_edition.catalog_entry_id == entry.id
        assert second_entry.collection_id == collection_id
        service.delete_edition(session, edition_id=second_edition.id)
        assert session.get(Edition, second_edition.id) is None
        service.delete_catalog_entry(session, entry_id=entry.id)
        assert session.get(CatalogEntry, second_entry.id) is not None
        assert session.scalar(select(func.count()).select_from(Edition)) == 0
        service.delete_catalog_entry(session, entry_id=second_entry.id)
        assert session.scalar(select(func.count()).select_from(CatalogEntry)) == 0
        assert session.scalar(select(func.count()).select_from(Edition)) == 0
        assert session.scalar(select(func.count()).select_from(Identifier)) == 0
        assert session.scalar(select(func.count()).select_from(InventoryItem)) == 0


def test_identifier_is_unique_per_edition_and_can_be_updated_or_deleted(database: Database) -> None:
    collection_id = add_collection(database, "Films")
    first_edition_id = add_edition(database, collection_id)
    second_edition_id = add_edition(database, collection_id, "Aliens")
    with database.session_factory() as session:
        service = InventoryService()
        identifier = service.create_identifier(
            session,
            edition_id=first_edition_id,
            identifier_type="ean",
            value="123",
            source="manual",
        )
        with pytest.raises(DuplicateIdentifierError):
            service.create_identifier(
                session,
                edition_id=first_edition_id,
                identifier_type="ean",
                value="123",
            )
        other_edition_identifier = service.create_identifier(
            session,
            edition_id=second_edition_id,
            identifier_type="ean",
            value="123",
        )
        updated = service.update_identifier(
            session,
            identifier_id=identifier.id,
            identifier_type="upc",
            value="456",
            source=None,
        )
        assert (updated.type, updated.value, updated.source) == ("upc", "456", None)
        service.delete_identifier(session, identifier_id=identifier.id)
        assert session.get(Identifier, identifier.id) is None
        assert session.get(Identifier, other_edition_identifier.id) is not None


def test_inventory_create_move_unassign_and_cross_collection_protection(database: Database) -> None:
    first_collection_id = add_collection(database, "Films")
    second_collection_id = add_collection(database, "Games")
    edition_id = add_edition(database, first_collection_id)
    first_location_id = add_location(database, first_collection_id, "Shelf A")
    second_location_id = add_location(database, first_collection_id, "Shelf B")
    foreign_location_id = add_location(database, second_collection_id, "Games Shelf")
    with database.session_factory() as session:
        service = InventoryService()
        unassigned = service.create_inventory_item(
            session,
            edition_id=edition_id,
            condition="good",
            notes="First copy",
        )
        assigned = service.create_inventory_item(
            session,
            edition_id=edition_id,
            location_id=first_location_id,
        )
        moved = service.move_inventory_item(
            session,
            item_id=unassigned.id,
            location_id=first_location_id,
        )
        assert moved.location_id == first_location_id
        assert (
            service.move_inventory_item(
                session,
                item_id=moved.id,
                location_id=first_location_id,
            ).location_id
            == first_location_id
        )
        assert (
            service.move_inventory_item(
                session,
                item_id=moved.id,
                location_id=second_location_id,
            ).location_id
            == second_location_id
        )
        assert (
            service.move_inventory_item(session, item_id=moved.id, location_id=None).location_id
            is None
        )
        updated = service.update_inventory_item(
            session,
            item_id=assigned.id,
            condition="excellent",
            notes="Updated",
        )
        assert (updated.condition, updated.notes) == ("excellent", "Updated")

        with pytest.raises(CrossCollectionLocationAssignmentError):
            service.create_inventory_item(
                session,
                edition_id=edition_id,
                location_id=foreign_location_id,
            )
        with pytest.raises(CrossCollectionLocationAssignmentError):
            service.move_inventory_item(
                session,
                item_id=assigned.id,
                location_id=foreign_location_id,
            )
        assert session.get(InventoryItem, assigned.id).location_id == first_location_id
        assert session.scalar(select(func.count()).select_from(InventoryItem)) == 2

        service.delete_inventory_item(session, item_id=assigned.id)
        assert session.get(InventoryItem, assigned.id) is None


def test_location_delete_requires_no_direct_inventory_items(database: Database) -> None:
    collection_id = add_collection(database, "Films")
    edition_id = add_edition(database, collection_id)
    location_id = add_location(database, collection_id, "Shelf")
    with database.session_factory() as session:
        inventory = InventoryService()
        locations = LocationHierarchyService()
        item = inventory.create_inventory_item(
            session,
            edition_id=edition_id,
            location_id=location_id,
        )
        with pytest.raises(LocationHasInventoryItemsError):
            locations.delete_location(session, location_id=location_id)
        inventory.move_inventory_item(session, item_id=item.id, location_id=None)
        locations.delete_location(session, location_id=location_id)
        assert session.get(Location, location_id) is None


def test_inventory_filters_support_exact_recursive_and_unassigned(database: Database) -> None:
    collection_id = add_collection(database, "Films")
    other_collection_id = add_collection(database, "Games")
    edition_id = add_edition(database, collection_id)
    root_id = add_location(database, collection_id, "Basement")
    shelf_id = add_location(database, collection_id, "Shelf", root_id)
    box_id = add_location(database, collection_id, "Box", shelf_id)
    other_location_id = add_location(database, collection_id, "Garage")
    foreign_location_id = add_location(database, other_collection_id, "Foreign")
    with database.session_factory() as session:
        service = InventoryService()
        root_item = service.create_inventory_item(
            session, edition_id=edition_id, location_id=root_id
        )
        shelf_item = service.create_inventory_item(
            session, edition_id=edition_id, location_id=shelf_id
        )
        box_item = service.create_inventory_item(session, edition_id=edition_id, location_id=box_id)
        garage_item = service.create_inventory_item(
            session,
            edition_id=edition_id,
            location_id=other_location_id,
        )
        unassigned_item = service.create_inventory_item(session, edition_id=edition_id)
        assert [
            item.id for item in service.list_inventory(session, collection_id=collection_id)
        ] == [
            root_item.id,
            shelf_item.id,
            box_item.id,
            garage_item.id,
            unassigned_item.id,
        ]
        assert [
            item.id
            for item in service.list_inventory(
                session,
                collection_id=collection_id,
                location_id=root_id,
            )
        ] == [root_item.id]
        assert [
            item.id
            for item in service.list_inventory(
                session,
                collection_id=collection_id,
                location_id=root_id,
                recursive=True,
            )
        ] == [root_item.id, shelf_item.id, box_item.id]
        assert [
            item.id
            for item in service.list_inventory(
                session,
                collection_id=collection_id,
                unassigned=True,
            )
        ] == [unassigned_item.id]
        with pytest.raises(CrossCollectionLocationAssignmentError):
            service.list_inventory(
                session,
                collection_id=collection_id,
                location_id=foreign_location_id,
            )


def test_collection_delete_cascades_locations_and_assigned_inventory(database: Database) -> None:
    collection_id = add_collection(database, "Films")
    edition_id = add_edition(database, collection_id)
    root_id = add_location(database, collection_id, "Root")
    child_id = add_location(database, collection_id, "Child", root_id)
    with database.session_factory() as session:
        inventory = InventoryService()
        inventory.create_identifier(
            session,
            edition_id=edition_id,
            identifier_type="ean",
            value="123",
        )
        inventory.create_inventory_item(session, edition_id=edition_id, location_id=root_id)
        inventory.create_inventory_item(session, edition_id=edition_id, location_id=child_id)
        collection = session.get(Collection, collection_id)
        assert collection is not None
        session.delete(collection)
        session.commit()
        for model in (CatalogEntry, Edition, Identifier, InventoryItem, Location):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_missing_catalog_entry_is_a_domain_error(database: Database) -> None:
    with database.session_factory() as session:
        with pytest.raises(CatalogEntryNotFoundError):
            InventoryService().update_catalog_entry(
                session,
                entry_id=999,
                display_title="Missing",
                entry_type="movie",
                sort_title=None,
                notes=None,
            )
