"""HTTP tests for collection ownership transfers."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.database import Database
from app.db.models import Collection, CollectionMember, User
from app.main import app
from tests.test_collection_api import session_token


@pytest.mark.anyio
@pytest.mark.parametrize("target_role", ["admin", "editor", "viewer", None])
async def test_owner_can_transfer_ownership_to_any_existing_user(
    database: Database, target_role: str | None
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        session.add_all([owner, target])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.flush()
        if target_role is not None:
            session.add(
                CollectionMember(collection_id=collection.id, user_id=target.id, role=target_role)
            )
        session.commit()
        collection_id, owner_id, target_id = collection.id, owner.id, target.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.post(
            f"/api/collections/{collection_id}/transfer-ownership",
            json={"username": " TARGET "},
        )
        assert response.status_code == 200
        assert response.json() == {"owner": "target"}
        client.cookies.set("stashive_session", session_token(database, target))
        assert (await client.get(f"/api/collections/{collection_id}")).json()["role"] == "owner"
        client.cookies.set("stashive_session", session_token(database, owner))
        assert (await client.get(f"/api/collections/{collection_id}")).json()["role"] == "admin"
    with database.session_factory() as session:
        collection = session.get(Collection, collection_id)
        memberships = session.scalars(
            select(CollectionMember).where(CollectionMember.collection_id == collection_id)
        ).all()
        assert collection is not None
        assert collection.owner_user_id == target_id
        assert {(member.user_id, member.role) for member in memberships} == {(owner_id, "admin")}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor_role", "expected"),
    [
        ("owner", 200),
        ("admin", 403),
        ("editor", 403),
        ("viewer", 403),
        ("outsider", 404),
        ("instance", 404),
    ],
)
async def test_ownership_transfer_permission_matrix(
    database: Database, actor_role: str, expected: int
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        users = {
            name: User(
                username=name,
                password_hash=f"{name}-password-hash",
                is_instance_admin=instance_admin,
            )
            for name, instance_admin in (
                ("owner", False),
                ("admin", False),
                ("editor", False),
                ("viewer", False),
                ("outsider", False),
                ("instance", True),
                ("target", False),
            )
        }
        session.add_all(users.values())
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=users["owner"].id)
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
        original_owner_id = users["owner"].id
        target_id = users["target"].id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, users[actor_role]))
        response = await client.post(
            f"/api/collections/{collection_id}/transfer-ownership", json={"username": "target"}
        )
    assert response.status_code == expected
    with database.session_factory() as session:
        collection = session.get(Collection, collection_id)
        memberships = session.scalars(
            select(CollectionMember).where(CollectionMember.collection_id == collection_id)
        ).all()
        assert collection is not None
        assert collection.owner_user_id == (target_id if expected == 200 else original_owner_id)
        if expected == 200:
            assert {(member.user_id, member.role) for member in memberships} == {
                (original_owner_id, "admin"),
                (users["admin"].id, "admin"),
                (users["editor"].id, "editor"),
                (users["viewer"].id, "viewer"),
            }
        else:
            assert {(member.user_id, member.role) for member in memberships} == {
                (users["admin"].id, "admin"),
                (users["editor"].id, "editor"),
                (users["viewer"].id, "viewer"),
            }


@pytest.mark.anyio
@pytest.mark.parametrize("actor_role", ["outsider", "instance"])
@pytest.mark.parametrize("target_username", ["member", "non-member", "missing"])
async def test_ownership_transfer_hides_target_details_from_non_members(
    database: Database, actor_role: str, target_username: str
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        member = User(username="member", password_hash="member-password-hash")
        non_member = User(username="non-member", password_hash="non-member-password-hash")
        outsider = User(username="outsider", password_hash="outsider-password-hash")
        instance = User(
            username="instance", password_hash="instance-password-hash", is_instance_admin=True
        )
        session.add_all([owner, member, non_member, outsider, instance])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.flush()
        session.add(CollectionMember(collection_id=collection.id, user_id=member.id, role="viewer"))
        session.commit()
        collection_id = collection.id
        actor = outsider if actor_role == "outsider" else instance
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, actor))
        response = await client.post(
            f"/api/collections/{collection_id}/transfer-ownership",
            json={"username": target_username},
        )
    assert response.status_code == 404
    assert response.json() == {"detail": "Collection not found"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("payload", "expected", "detail"),
    [
        ({"username": "owner"}, 409, "Ownership is already assigned to this user"),
        ({"username": "missing"}, 404, "User not found"),
        ({"username": "   "}, 422, None),
        ({}, 422, None),
    ],
)
async def test_ownership_transfer_rejects_invalid_targets_without_changing_data(
    database: Database, payload: dict[str, str], expected: int, detail: str | None
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        member = User(username="member", password_hash="member-password-hash")
        session.add_all([owner, member])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.flush()
        session.add(CollectionMember(collection_id=collection.id, user_id=member.id, role="viewer"))
        session.commit()
        collection_id, owner_id, member_id = collection.id, owner.id, member.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.post(
            f"/api/collections/{collection_id}/transfer-ownership", json=payload
        )
    assert response.status_code == expected
    if detail is not None:
        assert response.json() == {"detail": detail}
    with database.session_factory() as session:
        collection = session.get(Collection, collection_id)
        memberships = session.scalars(
            select(CollectionMember).where(CollectionMember.collection_id == collection_id)
        ).all()
        assert collection is not None
        assert collection.owner_user_id == owner_id
        assert {(item.user_id, item.role) for item in memberships} == {(member_id, "viewer")}


@pytest.mark.anyio
async def test_ownership_transfer_hides_legacy_and_missing_collections(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        legacy = Collection(name="Legacy", type="movies")
        session.add_all([owner, target, legacy])
        session.commit()
        legacy_id = legacy.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        for collection_id in (legacy_id, 999999):
            response = await client.post(
                f"/api/collections/{collection_id}/transfer-ownership", json={"username": "target"}
            )
            assert response.status_code == 404
            assert response.json() == {"detail": "Collection not found"}
    with database.session_factory() as session:
        assert session.get(Collection, legacy_id).owner_user_id is None
