"""HTTP and ACL tests for collection-scoped generic inventory metadata endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.service import AuthenticationService
from app.config import Settings
from app.db.database import Database
from app.db.models import CatalogEntry, Collection, CollectionMember, Edition, Identifier, User
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
