"""HTTP and ACL tests for collection-scoped generic inventory metadata endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.auth.service import AuthenticationService
from app.config import Settings
from app.db.database import Database
from app.db.models import (
    CatalogEntry,
    Collection,
    CollectionMember,
    Edition,
    Identifier,
    InventoryItem,
    Location,
    User,
)
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def inventory_context(database: Database) -> dict[str, int | dict[str, User]]:
    """Create one shared collection, a private collection, and all ACL roles."""
    with database.session_factory() as session:
        users: dict[str, User] = {}
        for name, instance_admin in (
            ("owner", False),
            ("admin", False),
            ("editor", False),
            ("viewer", False),
            ("outsider", False),
            ("instance", True),
        ):
            user = User(username=name, password_hash="hash", is_instance_admin=instance_admin)
            session.add(user)
            users[name] = user
        session.flush()
        collection = Collection(name="Films", type="movies", owner_user_id=users["owner"].id)
        other_collection = Collection(
            name="Games", type="board_games", owner_user_id=users["outsider"].id
        )
        legacy_collection = Collection(name="Legacy", type="movies")
        session.add_all([collection, other_collection, legacy_collection])
        session.flush()
        session.add_all(
            [
                CollectionMember(
                    collection_id=collection.id, user_id=users["admin"].id, role="admin"
                ),
                CollectionMember(
                    collection_id=collection.id, user_id=users["editor"].id, role="editor"
                ),
                CollectionMember(
                    collection_id=collection.id, user_id=users["viewer"].id, role="viewer"
                ),
            ]
        )
        session.commit()
        return {
            "users": users,
            "collection_id": collection.id,
            "other_collection_id": other_collection.id,
            "legacy_collection_id": legacy_collection.id,
        }


def authenticate(client: AsyncClient, database: Database, user: User) -> dict[str, str]:
    """Set a session cookie pair and return the required mutation header."""
    with database.session_factory() as session:
        stored_user = session.merge(user)
        token, csrf_token = AuthenticationService(Settings())._create_session(
            session,
            stored_user,
            __import__("app.auth.service", fromlist=["utc_now"]).utc_now(),
        )
        session.commit()
    client.cookies.set("stashive_session", token)
    client.cookies.set("stashive_csrf", csrf_token)
    return {"X-CSRF-Token": csrf_token}


def add_entry(database: Database, collection_id: int, title: str = "Alien") -> int:
    with database.session_factory() as session:
        entry = CatalogEntry(collection_id=collection_id, display_title=title, type="movie")
        session.add(entry)
        session.commit()
        return entry.id


def add_edition(database: Database, entry_id: int, name: str = "Blu-ray") -> int:
    with database.session_factory() as session:
        edition = Edition(catalog_entry_id=entry_id, display_name=name)
        session.add(edition)
        session.commit()
        return edition.id


@pytest.mark.anyio
async def test_title_search_and_transactional_add_item_cases(
    database: Database, inventory_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = inventory_context["collection_id"]
    users = inventory_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    alien_id = add_entry(database, collection_id, "Alien")
    existing_edition = add_edition(database, alien_id, "Special Edition")
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = authenticate(client, database, users["owner"])
        search = await client.get(f"/api/collections/{collection_id}/library/title-search?q=li")
        new_all = await client.post(
            f"/api/collections/{collection_id}/items",
            headers=headers,
            json={
                "title": {
                    "existing_id": None,
                    "new": {
                        "display_title": "Predator",
                        "type": "movie",
                        "sort_title": None,
                        "notes": None,
                    },
                },
                "edition": {
                    "existing_id": None,
                    "new": {"display_name": "UHD", "media_format": "UHD Blu-ray"},
                },
                "copy": {"condition": "Very Good", "notes": None, "location_id": None},
            },
        )
        new_edition = await client.post(
            f"/api/collections/{collection_id}/items",
            headers=headers,
            json={
                "title": {"existing_id": alien_id, "new": None},
                "edition": {
                    "existing_id": None,
                    "new": {"display_name": "DVD", "media_format": "DVD"},
                },
                "copy": {"condition": None, "notes": None, "location_id": None},
            },
        )
        extra_copy = await client.post(
            f"/api/collections/{collection_id}/items",
            headers=headers,
            json={
                "title": {"existing_id": alien_id, "new": None},
                "edition": {"existing_id": existing_edition, "new": None},
                "copy": {"condition": None, "notes": "second", "location_id": None},
            },
        )
    assert search.status_code == 200 and search.json()[0]["catalog_entry_id"] == alien_id
    assert new_all.status_code == new_edition.status_code == extra_copy.status_code == 201
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(CatalogEntry)) == 2
        assert session.scalar(select(func.count()).select_from(Edition)) == 3
        assert session.scalar(select(func.count()).select_from(InventoryItem)) == 3


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        ("owner", 200),
        ("admin", 200),
        ("editor", 200),
        ("viewer", 200),
        ("outsider", 404),
        ("instance", 404),
    ],
)
async def test_catalog_read_acl_and_stable_sorting(
    database: Database,
    inventory_context: dict[str, int | dict[str, User]],
    actor: str,
    expected: int,
) -> None:
    collection_id = inventory_context["collection_id"]
    users = inventory_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    first_id = add_entry(database, collection_id, "Zoo")
    second_id = add_entry(database, collection_id, "alpha")
    with database.session_factory() as session:
        session.get(CatalogEntry, first_id).sort_title = "Beta"
        session.commit()
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        authenticate(client, database, users[actor])
        listed = await client.get(f"/api/collections/{collection_id}/catalog-entries")
        detail = await client.get(f"/api/collections/{collection_id}/catalog-entries/{first_id}")
    assert listed.status_code == expected
    assert detail.status_code == expected
    if expected == 200:
        assert [entry["id"] for entry in listed.json()] == [second_id, first_id]
        assert set(detail.json()) == {
            "id",
            "collection_id",
            "display_title",
            "type",
            "sort_title",
            "notes",
        }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        ("owner", 201),
        ("admin", 201),
        ("editor", 201),
        ("viewer", 403),
        ("outsider", 404),
        ("instance", 404),
    ],
)
async def test_catalog_mutation_acl_matrix(
    database: Database,
    inventory_context: dict[str, int | dict[str, User]],
    actor: str,
    expected: int,
) -> None:
    collection_id = inventory_context["collection_id"]
    users = inventory_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = authenticate(client, database, users[actor])
        response = await client.post(
            f"/api/collections/{collection_id}/catalog-entries",
            json={"display_title": "Alien", "type": "movie"},
            headers=headers,
        )
    assert response.status_code == expected


@pytest.mark.anyio
async def test_catalog_patch_delete_and_scope_privacy(
    database: Database, inventory_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = inventory_context["collection_id"]
    other_collection_id = inventory_context["other_collection_id"]
    users = inventory_context["users"]
    assert (
        isinstance(collection_id, int)
        and isinstance(other_collection_id, int)
        and isinstance(users, dict)
    )
    entry_id = add_entry(database, collection_id)
    foreign_entry_id = add_entry(database, other_collection_id, "Private")
    legacy_collection_id = inventory_context["legacy_collection_id"]
    assert isinstance(legacy_collection_id, int)
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = authenticate(client, database, users["owner"])
        updated = await client.patch(
            f"/api/collections/{collection_id}/catalog-entries/{entry_id}",
            json={"sort_title": "The Alien", "notes": "Note"},
            headers=headers,
        )
        cleared = await client.patch(
            f"/api/collections/{collection_id}/catalog-entries/{entry_id}",
            json={"sort_title": None, "notes": None},
            headers=headers,
        )
        foreign = await client.get(
            f"/api/collections/{collection_id}/catalog-entries/{foreign_entry_id}"
        )
        invalid = await client.post(
            f"/api/collections/{collection_id}/catalog-entries",
            json={"display_title": "  ", "type": "movie"},
            headers=headers,
        )
        legacy = await client.get(f"/api/collections/{legacy_collection_id}/catalog-entries")
        missing = await client.get("/api/collections/999999/catalog-entries")
    assert updated.json()["sort_title"] == "The Alien"
    assert cleared.json()["sort_title"] is None and cleared.json()["notes"] is None
    assert foreign.status_code == 404 and invalid.status_code == 422
    assert legacy.status_code == 404 and missing.status_code == 404


@pytest.mark.anyio
async def test_edition_api_supports_acl_partial_nulls_and_collection_scope(
    database: Database, inventory_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = inventory_context["collection_id"]
    other_collection_id = inventory_context["other_collection_id"]
    users = inventory_context["users"]
    assert (
        isinstance(collection_id, int)
        and isinstance(other_collection_id, int)
        and isinstance(users, dict)
    )
    entry_id = add_entry(database, collection_id)
    foreign_entry_id = add_entry(database, other_collection_id, "Private")
    foreign_edition_id = add_edition(database, foreign_entry_id)
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_headers = authenticate(client, database, users["owner"])
        created = await client.post(
            f"/api/collections/{collection_id}/catalog-entries/{entry_id}/editions",
            json={"display_name": "Blu-ray", "publisher": "Fox", "language": "de"},
            headers=owner_headers,
        )
        edition_id = created.json()["id"]
        cleared = await client.patch(
            f"/api/collections/{collection_id}/editions/{edition_id}",
            json={"publisher": None, "language": None},
            headers=owner_headers,
        )
        foreign_nested = await client.get(
            f"/api/collections/{collection_id}/catalog-entries/{foreign_entry_id}/editions"
        )
        foreign_flat = await client.get(
            f"/api/collections/{collection_id}/editions/{foreign_edition_id}"
        )
        client.cookies.clear()
        viewer_headers = authenticate(client, database, users["viewer"])
        denied = await client.delete(
            f"/api/collections/{collection_id}/editions/{edition_id}", headers=viewer_headers
        )
    assert created.status_code == 201
    assert cleared.json()["publisher"] is None and cleared.json()["language"] is None
    assert foreign_nested.status_code == 404 and foreign_flat.status_code == 404
    assert denied.status_code == 403


@pytest.mark.anyio
async def test_identifier_api_handles_duplicates_updates_deletes_and_privacy(
    database: Database, inventory_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = inventory_context["collection_id"]
    other_collection_id = inventory_context["other_collection_id"]
    users = inventory_context["users"]
    assert (
        isinstance(collection_id, int)
        and isinstance(other_collection_id, int)
        and isinstance(users, dict)
    )
    entry_id = add_entry(database, collection_id)
    edition_id = add_edition(database, entry_id)
    second_edition_id = add_edition(database, entry_id, "DVD")
    foreign_edition_id = add_edition(database, add_entry(database, other_collection_id, "Private"))
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = authenticate(client, database, users["owner"])
        created = await client.post(
            f"/api/collections/{collection_id}/editions/{edition_id}/identifiers",
            json={"type": "ean", "value": "123", "source": "manual"},
            headers=headers,
        )
        identifier_id = created.json()["id"]
        duplicate = await client.post(
            f"/api/collections/{collection_id}/editions/{edition_id}/identifiers",
            json={"type": "ean", "value": "123"},
            headers=headers,
        )
        allowed_other = await client.post(
            f"/api/collections/{collection_id}/editions/{second_edition_id}/identifiers",
            json={"type": "ean", "value": "123"},
            headers=headers,
        )
        cleared = await client.patch(
            f"/api/collections/{collection_id}/editions/{edition_id}/identifiers/{identifier_id}",
            json={"source": None},
            headers=headers,
        )
        foreign = await client.get(
            f"/api/collections/{collection_id}/editions/{foreign_edition_id}/identifiers"
        )
        deleted = await client.delete(
            f"/api/collections/{collection_id}/editions/{edition_id}/identifiers/{identifier_id}",
            headers=headers,
        )
    assert (
        created.status_code == 201
        and duplicate.status_code == 409
        and allowed_other.status_code == 201
    )
    assert cleared.json()["source"] is None
    assert foreign.status_code == 404 and deleted.status_code == 204
    with database.session_factory() as session:
        assert session.get(Identifier, identifier_id) is None


@pytest.mark.anyio
async def test_inventory_item_api_supports_assignment_moves_filters_and_privacy(
    database: Database, inventory_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = inventory_context["collection_id"]
    other_collection_id = inventory_context["other_collection_id"]
    users = inventory_context["users"]
    assert (
        isinstance(collection_id, int)
        and isinstance(other_collection_id, int)
        and isinstance(users, dict)
    )
    edition_id = add_edition(database, add_entry(database, collection_id))
    foreign_edition_id = add_edition(database, add_entry(database, other_collection_id, "Private"))
    with database.session_factory() as session:
        root = Location(collection_id=collection_id, name="Basement", type="room")
        foreign = Location(collection_id=other_collection_id, name="Private", type="room")
        session.add_all([root, foreign])
        session.flush()
        child = Location(collection_id=collection_id, parent_id=root.id, name="Shelf", type="shelf")
        session.add(child)
        session.commit()
        root_id, child_id, foreign_location_id = root.id, child.id, foreign.id
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = authenticate(client, database, users["owner"])
        first = await client.post(
            f"/api/collections/{collection_id}/inventory-items",
            json={"edition_id": edition_id, "condition": "good", "location_id": root_id},
            headers=headers,
        )
        item_id = first.json()["id"]
        second = await client.post(
            f"/api/collections/{collection_id}/inventory-items",
            json={"edition_id": edition_id},
            headers=headers,
        )
        moved = await client.patch(
            f"/api/collections/{collection_id}/inventory-items/{item_id}",
            json={"location_id": child_id, "notes": "Moved"},
            headers=headers,
        )
        exact = await client.get(
            f"/api/collections/{collection_id}/inventory-items?location_id={root_id}&include_descendants=false"
        )
        recursive = await client.get(
            f"/api/collections/{collection_id}/inventory-items?location_id={root_id}"
        )
        unassigned = await client.get(
            f"/api/collections/{collection_id}/inventory-items?unassigned=true"
        )
        conflict = await client.get(
            f"/api/collections/{collection_id}/inventory-items?location_id={root_id}&unassigned=true"
        )
        foreign_edition = await client.post(
            f"/api/collections/{collection_id}/inventory-items",
            json={"edition_id": foreign_edition_id},
            headers=headers,
        )
        foreign_location = await client.patch(
            f"/api/collections/{collection_id}/inventory-items/{item_id}",
            json={"location_id": foreign_location_id},
            headers=headers,
        )
        cleared = await client.patch(
            f"/api/collections/{collection_id}/inventory-items/{item_id}",
            json={"location_id": None, "condition": None},
            headers=headers,
        )
    assert first.status_code == 201 and second.status_code == 201
    assert moved.json()["location_id"] == child_id and moved.json()["notes"] == "Moved"
    assert exact.json() == [] and [item["id"] for item in recursive.json()] == [item_id]
    assert [item["id"] for item in unassigned.json()] == [second.json()["id"]]
    assert (
        conflict.status_code == 422
        and foreign_edition.status_code == 404
        and foreign_location.status_code == 404
    )
    assert cleared.json()["location_id"] is None and cleared.json()["condition"] is None


@pytest.mark.anyio
async def test_library_summaries_group_and_filter_matching_copies(
    database: Database, inventory_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = inventory_context["collection_id"]
    other_collection_id = inventory_context["other_collection_id"]
    users = inventory_context["users"]
    assert (
        isinstance(collection_id, int)
        and isinstance(other_collection_id, int)
        and isinstance(users, dict)
    )
    alien_id = add_entry(database, collection_id, "Alien")
    alien_blu_ray = add_edition(database, alien_id, "Blu-ray")
    alien_uhd = add_edition(database, alien_id, "UHD")
    heat_id = add_entry(database, collection_id, "Heat")
    heat_dvd = add_edition(database, heat_id, "DVD")
    empty_id = add_entry(database, collection_id, "Empty")
    add_edition(database, empty_id, "VHS")
    with database.session_factory() as session:
        root = Location(collection_id=collection_id, name="Room", type="room")
        foreign = Location(collection_id=other_collection_id, name="Private", type="room")
        session.add_all([root, foreign])
        session.flush()
        child = Location(collection_id=collection_id, parent_id=root.id, name="Shelf", type="shelf")
        session.add(child)
        session.flush()
        session.add_all(
            [
                InventoryItem(edition_id=alien_blu_ray, location_id=root.id),
                InventoryItem(edition_id=alien_uhd, location_id=child.id),
                InventoryItem(edition_id=alien_uhd),
                InventoryItem(edition_id=heat_dvd, location_id=child.id),
            ]
        )
        session.get(Edition, alien_blu_ray).media_format = "Blu-ray"
        session.get(Edition, alien_uhd).media_format = "UHD Blu-ray"
        session.commit()
        root_id, foreign_id = root.id, foreign.id
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        authenticate(client, database, users["viewer"])
        unfiltered = await client.get(f"/api/collections/{collection_id}/library")
        exact = await client.get(
            f"/api/collections/{collection_id}/library?location_id={root_id}&include_descendants=false"
        )
        recursive = await client.get(
            f"/api/collections/{collection_id}/library?location_id={root_id}"
        )
        unassigned = await client.get(f"/api/collections/{collection_id}/library?unassigned=true")
        conflict = await client.get(
            f"/api/collections/{collection_id}/library?location_id={root_id}&unassigned=true"
        )
        invalid = await client.get(
            f"/api/collections/{collection_id}/library?include_descendants=false"
        )
        foreign = await client.get(
            f"/api/collections/{collection_id}/library?location_id={foreign_id}"
        )
        client.cookies.clear()
        authenticate(client, database, users["instance"])
        inaccessible = await client.get(f"/api/collections/{collection_id}/library")
    assert [
        (title["display_title"], title["edition_count"], title["copy_count"])
        for title in unfiltered.json()
    ] == [("Alien", 2, 3), ("Empty", 1, 0), ("Heat", 1, 1)]
    assert unfiltered.json()[0]["media_formats"] == ["Blu-ray", "UHD Blu-ray"]
    assert [
        (title["display_title"], title["edition_count"], title["copy_count"])
        for title in exact.json()
    ] == [("Alien", 1, 1)]
    assert [
        (title["display_title"], title["edition_count"], title["copy_count"])
        for title in recursive.json()
    ] == [("Alien", 2, 2), ("Heat", 1, 1)]
    assert [
        (title["display_title"], title["edition_count"], title["copy_count"])
        for title in unassigned.json()
    ] == [("Alien", 1, 1)]
    assert conflict.status_code == 422 and invalid.status_code == 422 and foreign.status_code == 404
    assert inaccessible.status_code == 404
