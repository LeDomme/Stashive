"""HTTP access-control tests for collection CRUD."""

import pytest
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.service import AuthenticationService
from app.config import Settings
from app.db.database import Database
from app.db.models import CatalogEntry, Collection, CollectionMember, Edition, InventoryItem, User
from app.main import app

password_hasher = PasswordHasher()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def users(database: Database) -> dict[str, User]:
    with database.session_factory() as session:
        result = {}
        for name, instance_admin in (
            ("owner", False),
            ("admin", False),
            ("editor", False),
            ("viewer", False),
            ("outsider", False),
            ("instance", True),
        ):
            user = User(
                username=name,
                password_hash=password_hasher.hash("password"),
                is_instance_admin=instance_admin,
            )
            session.add(user)
            result[name] = user
        session.commit()
        return result


def session_token(database: Database, user: User) -> str:
    with database.session_factory() as session:
        stored = session.merge(user)
        token, _ = AuthenticationService(Settings())._create_session(
            session, stored, __import__("app.auth.service", fromlist=["utc_now"]).utc_now()
        )
        session.commit()
        return token


@pytest.mark.anyio
async def test_collection_crud_acl(database: Database, users: dict[str, User]) -> None:
    app.state.database = database
    with database.session_factory() as session:
        collection = Collection(name="Private", type="movies", owner_user_id=users["owner"].id)
        legacy = Collection(name="Legacy", type="movies")
        session.add_all([collection, legacy])
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
        collection_id, legacy_id = collection.id, legacy.id
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for role in ("owner", "admin", "editor", "viewer"):
            client.cookies.set("stashive_session", session_token(database, users[role]))
            assert (await client.get(f"/api/collections/{collection_id}")).status_code == 200
            listed = await client.get("/api/collections")
            assert [item["id"] for item in listed.json()] == [collection_id]
        client.cookies.set("stashive_session", session_token(database, users["outsider"]))
        assert (await client.get(f"/api/collections/{collection_id}")).status_code == 404
        assert (await client.get(f"/api/collections/{legacy_id}")).status_code == 404
        assert (await client.get("/api/collections")).json() == []
        assert (await client.get("/api/collections/999999")).status_code == 404
        client.cookies.set("stashive_session", session_token(database, users["instance"]))
        assert (await client.get(f"/api/collections/{collection_id}")).status_code == 404
        assert (await client.get("/api/collections")).json() == []
        client.cookies.set("stashive_session", session_token(database, users["admin"]))
        assert (
            await client.patch(
                f"/api/collections/{collection_id}", json={"name": "Changed", "type": "movies"}
            )
        ).status_code == 200
        client.cookies.set("stashive_session", session_token(database, users["editor"]))
        assert (
            await client.patch(
                f"/api/collections/{collection_id}", json={"name": "Denied", "type": "movies"}
            )
        ).status_code == 403
        client.cookies.set("stashive_session", session_token(database, users["owner"]))
        created = await client.post(
            "/api/collections",
            json={"name": "Created", "type": "movies", "owner_user_id": users["outsider"].id},
        )
        assert created.status_code == 201
        with database.session_factory() as session:
            assert session.get(Collection, created.json()["id"]).owner_user_id == users["owner"].id
            entry = CatalogEntry(collection_id=collection_id, display_title="Title", type="movie")
            edition = Edition(display_name="Edition")
            edition.inventory_items.append(InventoryItem())
            entry.editions.append(edition)
            session.add(entry)
            session.commit()
        assert (await client.delete(f"/api/collections/{collection_id}")).status_code == 204
        with database.session_factory() as session:
            assert session.get(Collection, collection_id) is None
            assert session.scalar(select(CatalogEntry)) is None
            assert session.scalar(select(Edition)) is None
            assert session.scalar(select(InventoryItem)) is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor", "method", "expected"),
    [
        ("owner", "PATCH", 200),
        ("admin", "PATCH", 200),
        ("editor", "PATCH", 403),
        ("viewer", "PATCH", 403),
        ("outsider", "PATCH", 404),
        ("instance", "PATCH", 404),
        ("owner", "DELETE", 204),
        ("admin", "DELETE", 403),
        ("editor", "DELETE", 403),
        ("viewer", "DELETE", 403),
        ("outsider", "DELETE", 404),
        ("instance", "DELETE", 404),
    ],
)
async def test_patch_delete_role_matrix(
    database: Database,
    users: dict[str, User],
    actor: str,
    method: str,
    expected: int,
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        collection = Collection(name="Private", type="movies", owner_user_id=users["owner"].id)
        session.add(collection)
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
        collection_id = collection.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, users[actor]))
        if method == "PATCH":
            response = await client.patch(
                f"/api/collections/{collection_id}",
                json={"name": "Updated", "type": "movies"},
            )
        else:
            response = await client.delete(f"/api/collections/{collection_id}")
    assert response.status_code == expected
    with database.session_factory() as session:
        collection = session.get(Collection, collection_id)
        if expected == 204:
            assert collection is None
        else:
            assert collection is not None
            assert collection.name == ("Updated" if expected == 200 else "Private")


@pytest.mark.anyio
async def test_ownerless_collection_patch_and_delete_are_hidden(
    database: Database, users: dict[str, User]
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        legacy = Collection(name="Legacy", type="movies")
        session.add(legacy)
        session.commit()
        legacy_id = legacy.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, users["owner"]))
        response = await client.patch(
            f"/api/collections/{legacy_id}",
            json={"name": "Changed", "type": "movies"},
        )
        assert response.status_code == 404
        assert (await client.delete(f"/api/collections/{legacy_id}")).status_code == 404
    with database.session_factory() as session:
        assert session.get(Collection, legacy_id).name == "Legacy"
