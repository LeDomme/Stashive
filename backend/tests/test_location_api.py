"""HTTP and ACL tests for collection-scoped location tree endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.service import AuthenticationService
from app.config import Settings
from app.db.database import Database
from app.db.models import Collection, CollectionMember, Location, User
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def location_context(database: Database) -> dict[str, int | dict[str, User]]:
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


def credentials(database: Database, user: User) -> tuple[str, str]:
    with database.session_factory() as session:
        stored_user = session.merge(user)
        token, csrf_token = AuthenticationService(Settings())._create_session(
            session,
            stored_user,
            __import__("app.auth.service", fromlist=["utc_now"]).utc_now(),
        )
        session.commit()
        return token, csrf_token


def authenticate(client: AsyncClient, database: Database, user: User) -> str:
    token, csrf_token = credentials(database, user)
    client.cookies.set("stashive_session", token)
    client.cookies.set("stashive_csrf", csrf_token)
    return csrf_token


def mutation_headers(csrf_token: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf_token}


@pytest.mark.anyio
async def test_location_tree_reads_nested_nodes_in_deterministic_name_id_order(
    database: Database, location_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = location_context["collection_id"]
    assert isinstance(collection_id, int)
    users = location_context["users"]
    assert isinstance(users, dict)
    with database.session_factory() as session:
        zoo = Location(collection_id=collection_id, name="Zoo", type="room")
        alpha = Location(collection_id=collection_id, name="alpha", type="room")
        duplicate_first = Location(collection_id=collection_id, name="Same", type="shelf")
        duplicate_second = Location(collection_id=collection_id, name="same", type="shelf")
        session.add_all([zoo, alpha, duplicate_first, duplicate_second])
        session.flush()
        basement = Location(
            collection_id=collection_id, parent_id=alpha.id, name="Basement", type="room"
        )
        session.add(basement)
        session.flush()
        shelf = Location(
            collection_id=collection_id, parent_id=basement.id, name="Shelf", type="shelf"
        )
        session.add(shelf)
        session.commit()
        duplicate_ids = [duplicate_first.id, duplicate_second.id]
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        authenticate(client, database, users["owner"])
        response = await client.get(f"/api/collections/{collection_id}/locations")
    assert response.status_code == 200
    tree = response.json()
    assert [node["name"] for node in tree] == ["alpha", "Same", "same", "Zoo"]
    assert [node["id"] for node in tree[1:3]] == duplicate_ids
    assert tree[0]["children"][0]["name"] == "Basement"
    assert tree[0]["children"][0]["children"][0]["name"] == "Shelf"
    assert set(tree[0]) == {
        "id",
        "collection_id",
        "parent_id",
        "name",
        "type",
        "description",
        "children",
    }


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
async def test_location_tree_read_acl_matrix(
    database: Database,
    location_context: dict[str, int | dict[str, User]],
    actor: str,
    expected: int,
) -> None:
    collection_id = location_context["collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        authenticate(client, database, users[actor])
        response = await client.get(f"/api/collections/{collection_id}/locations")
    assert response.status_code == expected


@pytest.mark.anyio
async def test_location_tree_hides_legacy_missing_and_unauthenticated_collections(
    database: Database, location_context: dict[str, int | dict[str, User]]
) -> None:
    legacy_collection_id = location_context["legacy_collection_id"]
    users = location_context["users"]
    assert isinstance(legacy_collection_id, int) and isinstance(users, dict)
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/collections/999999/locations")).status_code == 401
        authenticate(client, database, users["owner"])
        legacy_response = await client.get(f"/api/collections/{legacy_collection_id}/locations")
        assert legacy_response.status_code == 404
        assert (await client.get("/api/collections/999999/locations")).status_code == 404


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
async def test_location_create_acl_matrix(
    database: Database,
    location_context: dict[str, int | dict[str, User]],
    actor: str,
    expected: int,
) -> None:
    collection_id = location_context["collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        csrf_token = authenticate(client, database, users[actor])
        response = await client.post(
            f"/api/collections/{collection_id}/locations",
            json={"name": f"{actor} root", "type": "room", "description": "Physical room"},
            headers=mutation_headers(csrf_token),
        )
    assert response.status_code == expected
    if expected == 201:
        assert response.json()["parent_id"] is None
        assert response.json()["collection_id"] == collection_id


@pytest.mark.anyio
async def test_location_create_child_validates_input_parent_scope_and_csrf(
    database: Database, location_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = location_context["collection_id"]
    other_collection_id = location_context["other_collection_id"]
    legacy_collection_id = location_context["legacy_collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int)
    assert isinstance(other_collection_id, int)
    assert isinstance(legacy_collection_id, int)
    assert isinstance(users, dict)
    with database.session_factory() as session:
        parent = Location(collection_id=collection_id, name="Parent", type="room")
        foreign_parent = Location(collection_id=other_collection_id, name="Private", type="room")
        session.add_all([parent, foreign_parent])
        session.commit()
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unauthenticated = await client.post(
            f"/api/collections/{collection_id}/locations", json={"name": "Denied", "type": "box"}
        )
        csrf_token = authenticate(client, database, users["owner"])
        url = f"/api/collections/{collection_id}/locations"
        missing_csrf = await client.post(url, json={"name": "Denied", "type": "box"})
        assert missing_csrf.status_code == 403
        child = await client.post(
            url,
            json={"name": "Child", "type": "box", "parent_id": parent.id, "description": None},
            headers=mutation_headers(csrf_token),
        )
        foreign = await client.post(
            url,
            json={"name": "Leaking", "type": "box", "parent_id": foreign_parent.id},
            headers=mutation_headers(csrf_token),
        )
        missing_parent = await client.post(
            url,
            json={"name": "Missing", "type": "box", "parent_id": 999999},
            headers=mutation_headers(csrf_token),
        )
        invalid_type = await client.post(
            url,
            json={"name": "Invalid", "type": "crate"},
            headers=mutation_headers(csrf_token),
        )
        blank_name = await client.post(
            url,
            json={"name": " ", "type": "box"},
            headers=mutation_headers(csrf_token),
        )
        legacy = await client.post(
            f"/api/collections/{legacy_collection_id}/locations",
            json={"name": "Legacy", "type": "box"},
            headers=mutation_headers(csrf_token),
        )
        missing_collection = await client.post(
            "/api/collections/999999/locations",
            json={"name": "Missing collection", "type": "box"},
            headers=mutation_headers(csrf_token),
        )
    assert unauthenticated.status_code == 401
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent.id
    assert foreign.status_code == 404
    assert missing_parent.status_code == 404
    assert invalid_type.status_code == 422
    assert blank_name.status_code == 422
    assert legacy.status_code == 404
    assert missing_collection.status_code == 404


@pytest.mark.anyio
async def test_location_patch_supports_partial_metadata_and_reparenting(
    database: Database, location_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = location_context["collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    with database.session_factory() as session:
        first_parent = Location(collection_id=collection_id, name="First", type="room")
        second_parent = Location(collection_id=collection_id, name="Second", type="room")
        session.add_all([first_parent, second_parent])
        session.flush()
        child = Location(
            collection_id=collection_id,
            parent_id=first_parent.id,
            name="Child",
            type="shelf",
            description="Old",
        )
        session.add(child)
        session.commit()
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        csrf_token = authenticate(client, database, users["owner"])
        url = f"/api/collections/{collection_id}/locations/{child.id}"
        renamed = await client.patch(
            url, json={"name": "Renamed"}, headers=mutation_headers(csrf_token)
        )
        changed_type = await client.patch(
            url, json={"type": "box"}, headers=mutation_headers(csrf_token)
        )
        cleared_description = await client.patch(
            url, json={"description": None}, headers=mutation_headers(csrf_token)
        )
        moved = await client.patch(
            url, json={"parent_id": second_parent.id}, headers=mutation_headers(csrf_token)
        )
        moved_to_root = await client.patch(
            url, json={"parent_id": None}, headers=mutation_headers(csrf_token)
        )
        nested_root = await client.patch(
            f"/api/collections/{collection_id}/locations/{first_parent.id}",
            json={"parent_id": child.id},
            headers=mutation_headers(csrf_token),
        )
    assert renamed.json()["name"] == "Renamed"
    assert changed_type.json()["type"] == "box"
    assert cleared_description.json()["description"] is None
    assert moved.json()["parent_id"] == second_parent.id
    assert moved_to_root.json()["parent_id"] is None
    assert nested_root.json()["parent_id"] == child.id


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        ("owner", 200),
        ("admin", 200),
        ("editor", 200),
        ("viewer", 403),
        ("outsider", 404),
        ("instance", 404),
    ],
)
async def test_location_patch_acl_matrix(
    database: Database,
    location_context: dict[str, int | dict[str, User]],
    actor: str,
    expected: int,
) -> None:
    collection_id = location_context["collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    with database.session_factory() as session:
        location = Location(collection_id=collection_id, name="Original", type="shelf")
        session.add(location)
        session.commit()
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        csrf_token = authenticate(client, database, users[actor])
        response = await client.patch(
            f"/api/collections/{collection_id}/locations/{location.id}",
            json={"name": "Updated"},
            headers=mutation_headers(csrf_token),
        )
    assert response.status_code == expected
    with database.session_factory() as session:
        stored = session.get(Location, location.id)
        assert stored.name == ("Updated" if expected == 200 else "Original")


@pytest.mark.anyio
async def test_location_patch_rejects_cycles_cross_scope_and_preserves_state(
    database: Database, location_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = location_context["collection_id"]
    other_collection_id = location_context["other_collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int)
    assert isinstance(other_collection_id, int)
    assert isinstance(users, dict)
    with database.session_factory() as session:
        first = Location(collection_id=collection_id, name="First", type="room")
        session.add(first)
        session.flush()
        second = Location(
            collection_id=collection_id, parent_id=first.id, name="Second", type="shelf"
        )
        session.add(second)
        session.flush()
        third = Location(collection_id=collection_id, parent_id=second.id, name="Third", type="box")
        foreign = Location(collection_id=other_collection_id, name="Foreign", type="room")
        session.add_all([third, foreign])
        session.commit()
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        csrf_token = authenticate(client, database, users["owner"])
        first_url = f"/api/collections/{collection_id}/locations/{first.id}"
        self_parent = await client.patch(
            first_url, json={"parent_id": first.id}, headers=mutation_headers(csrf_token)
        )
        direct_cycle = await client.patch(
            first_url, json={"parent_id": second.id}, headers=mutation_headers(csrf_token)
        )
        indirect_cycle = await client.patch(
            first_url, json={"parent_id": third.id}, headers=mutation_headers(csrf_token)
        )
        foreign_parent = await client.patch(
            first_url, json={"parent_id": foreign.id}, headers=mutation_headers(csrf_token)
        )
        foreign_location = await client.patch(
            f"/api/collections/{collection_id}/locations/{foreign.id}",
            json={"name": "Leak"},
            headers=mutation_headers(csrf_token),
        )
        unknown_location = await client.patch(
            f"/api/collections/{collection_id}/locations/999999",
            json={"name": "Unknown"},
            headers=mutation_headers(csrf_token),
        )
    cycle_statuses = [
        response.status_code for response in (self_parent, direct_cycle, indirect_cycle)
    ]
    assert cycle_statuses == [409] * 3
    assert foreign_parent.status_code == 404
    assert foreign_location.status_code == 404
    assert unknown_location.status_code == 404
    with database.session_factory() as session:
        assert session.get(Location, first.id).parent_id is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        ("owner", 204),
        ("admin", 204),
        ("editor", 204),
        ("viewer", 403),
        ("outsider", 404),
        ("instance", 404),
    ],
)
async def test_location_delete_acl_matrix(
    database: Database,
    location_context: dict[str, int | dict[str, User]],
    actor: str,
    expected: int,
) -> None:
    collection_id = location_context["collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int) and isinstance(users, dict)
    with database.session_factory() as session:
        location = Location(collection_id=collection_id, name=f"{actor} leaf", type="box")
        session.add(location)
        session.commit()
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        csrf_token = authenticate(client, database, users[actor])
        response = await client.delete(
            f"/api/collections/{collection_id}/locations/{location.id}",
            headers=mutation_headers(csrf_token),
        )
    assert response.status_code == expected
    with database.session_factory() as session:
        assert (session.get(Location, location.id) is None) is (expected == 204)


@pytest.mark.anyio
async def test_location_delete_rejects_non_leaf_and_hides_cross_collection_ids(
    database: Database, location_context: dict[str, int | dict[str, User]]
) -> None:
    collection_id = location_context["collection_id"]
    other_collection_id = location_context["other_collection_id"]
    users = location_context["users"]
    assert isinstance(collection_id, int)
    assert isinstance(other_collection_id, int)
    assert isinstance(users, dict)
    with database.session_factory() as session:
        parent = Location(collection_id=collection_id, name="Parent", type="room")
        foreign = Location(collection_id=other_collection_id, name="Foreign", type="room")
        session.add_all([parent, foreign])
        session.flush()
        child = Location(collection_id=collection_id, parent_id=parent.id, name="Child", type="box")
        session.add(child)
        session.commit()
    app.state.database = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        csrf_token = authenticate(client, database, users["owner"])
        blocked = await client.delete(
            f"/api/collections/{collection_id}/locations/{parent.id}",
            headers=mutation_headers(csrf_token),
        )
        foreign_location = await client.delete(
            f"/api/collections/{collection_id}/locations/{foreign.id}",
            headers=mutation_headers(csrf_token),
        )
        unknown_location = await client.delete(
            f"/api/collections/{collection_id}/locations/999999",
            headers=mutation_headers(csrf_token),
        )
    assert blocked.status_code == 409
    assert foreign_location.status_code == 404
    assert unknown_location.status_code == 404
    with database.session_factory() as session:
        assert session.get(Location, parent.id) is not None
        assert session.get(Location, child.id) is not None
