"""Domain tests for the collection-scoped location hierarchy."""

import pytest
from sqlalchemy import func, select

from app.db.database import Database
from app.db.models import Collection, Location
from app.locations.service import (
    InvalidLocationNameError,
    InvalidLocationTypeError,
    LocationCycleError,
    LocationHasChildrenError,
    LocationHierarchyService,
    LocationNotFoundError,
    ParentCollectionMismatchError,
    ParentNotFoundError,
    SelfParentError,
)


def add_collection(database: Database, name: str = "Films") -> int:
    with database.session_factory() as session:
        collection = Collection(name=name, type="movies")
        session.add(collection)
        session.commit()
        return collection.id


def create_location(
    database: Database,
    collection_id: int,
    name: str,
    *,
    parent_id: int | None = None,
    location_type: str = "shelf",
    description: str | None = None,
) -> Location:
    with database.session_factory() as session:
        return LocationHierarchyService().create_location(
            session,
            collection_id=collection_id,
            name=name,
            location_type=location_type,
            description=description,
            parent_id=parent_id,
        )


def test_create_supports_roots_children_depth_and_duplicate_names(database: Database) -> None:
    collection_id = add_collection(database)
    house = create_location(database, collection_id, "House", location_type="room")
    duplicate = create_location(database, collection_id, "House", location_type="room")
    basement = create_location(database, collection_id, "Basement", parent_id=house.id)
    shelf = create_location(database, collection_id, "Shelf", parent_id=basement.id)
    box = create_location(database, collection_id, "Box", parent_id=shelf.id)

    parent_ids = (
        house.parent_id,
        duplicate.parent_id,
        basement.parent_id,
        shelf.parent_id,
        box.parent_id,
    )
    assert parent_ids == (
        None,
        None,
        house.id,
        basement.id,
        shelf.id,
    )


def test_create_rejects_invalid_input_and_cross_collection_parent(database: Database) -> None:
    first_collection_id = add_collection(database, "Films")
    second_collection_id = add_collection(database, "Games")
    parent = create_location(database, first_collection_id, "Shelf")
    with database.session_factory() as session:
        service = LocationHierarchyService()
        with pytest.raises(ParentCollectionMismatchError):
            service.create_location(
                session,
                collection_id=second_collection_id,
                name="Box",
                location_type="box",
                parent_id=parent.id,
            )
        with pytest.raises(ParentNotFoundError):
            service.create_location(
                session,
                collection_id=first_collection_id,
                name="Box",
                location_type="box",
                parent_id=999,
            )
        with pytest.raises(InvalidLocationNameError):
            service.create_location(
                session, collection_id=first_collection_id, name=" ", location_type="box"
            )
        with pytest.raises(InvalidLocationTypeError):
            service.create_location(
                session, collection_id=first_collection_id, name="Box", location_type="crate"
            )


def test_update_metadata_normalizes_and_replaces_all_editable_fields(database: Database) -> None:
    collection_id = add_collection(database)
    location = create_location(database, collection_id, "Old", description="Old description")
    with database.session_factory() as session:
        updated = LocationHierarchyService().update_metadata(
            session,
            location_id=location.id,
            name=" New ",
            location_type="CABINET",
            description=" New description ",
        )
    assert (updated.name, updated.type, updated.description) == (
        "New",
        "cabinet",
        "New description",
    )


def test_invalid_metadata_update_leaves_the_stored_location_unchanged(database: Database) -> None:
    collection_id = add_collection(database)
    location = create_location(database, collection_id, "Shelf", description="Original")
    with database.session_factory() as session:
        with pytest.raises(InvalidLocationTypeError):
            LocationHierarchyService().update_metadata(
                session,
                location_id=location.id,
                name="Changed",
                location_type="invalid",
                description="Changed",
            )
        session.rollback()
    with database.session_factory() as session:
        stored = session.get(Location, location.id)
        assert (stored.name, stored.type, stored.description) == ("Shelf", "shelf", "Original")


def test_reparent_supports_moving_children_roots_and_roots_to_children(database: Database) -> None:
    collection_id = add_collection(database)
    first_parent = create_location(database, collection_id, "First")
    second_parent = create_location(database, collection_id, "Second")
    child = create_location(database, collection_id, "Child", parent_id=first_parent.id)
    with database.session_factory() as session:
        service = LocationHierarchyService()
        moved = service.reparent_location(
            session, location_id=child.id, parent_id=second_parent.id
        )
        assert moved.parent_id == second_parent.id
        moved_to_root = service.reparent_location(session, location_id=child.id, parent_id=None)
        assert moved_to_root.parent_id is None
        nested_root = service.reparent_location(
            session, location_id=first_parent.id, parent_id=child.id
        )
        assert nested_root.parent_id == child.id


def test_reparent_rejects_self_cycles_cross_collection_and_missing_locations(
    database: Database,
) -> None:
    collection_id = add_collection(database)
    other_collection_id = add_collection(database, "Games")
    first = create_location(database, collection_id, "First")
    second = create_location(database, collection_id, "Second", parent_id=first.id)
    third = create_location(database, collection_id, "Third", parent_id=second.id)
    other = create_location(database, other_collection_id, "Other")
    with database.session_factory() as session:
        service = LocationHierarchyService()
        with pytest.raises(SelfParentError):
            service.reparent_location(session, location_id=first.id, parent_id=first.id)
        with pytest.raises(LocationCycleError):
            service.reparent_location(session, location_id=first.id, parent_id=second.id)
        with pytest.raises(LocationCycleError):
            service.reparent_location(session, location_id=first.id, parent_id=third.id)
        with pytest.raises(ParentCollectionMismatchError):
            service.reparent_location(session, location_id=second.id, parent_id=other.id)
        with pytest.raises(ParentNotFoundError):
            service.reparent_location(session, location_id=second.id, parent_id=999)
        with pytest.raises(LocationNotFoundError):
            service.reparent_location(session, location_id=999, parent_id=None)


def test_delete_allows_leaves_and_rejects_non_leaves_without_changing_tree(
    database: Database,
) -> None:
    collection_id = add_collection(database)
    parent = create_location(database, collection_id, "Parent")
    child = create_location(database, collection_id, "Child", parent_id=parent.id)
    with database.session_factory() as session:
        service = LocationHierarchyService()
        with pytest.raises(LocationHasChildrenError):
            service.delete_location(session, location_id=parent.id)
        assert session.get(Location, parent.id) is not None
        assert session.get(Location, child.id) is not None
        service.delete_location(session, location_id=child.id)
        service.delete_location(session, location_id=parent.id)
    with database.session_factory() as session:
        assert session.scalar(select(Location.id)) is None


def test_collection_delete_cascades_entire_location_tree(database: Database) -> None:
    collection_id = add_collection(database)
    root = create_location(database, collection_id, "Root")
    child = create_location(database, collection_id, "Child", parent_id=root.id)
    create_location(database, collection_id, "Grandchild", parent_id=child.id)
    with database.session_factory() as session:
        session.delete(session.get(Collection, collection_id))
        session.commit()
        assert session.scalar(select(func.count()).select_from(Location)) == 0
