"""HTTP ACL tests for collection member endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.database import Database
from app.db.models import Collection, CollectionMember, User
from app.main import app
from tests.test_collection_api import session_token


@pytest.mark.anyio
async def test_member_api_acl(database: Database) -> None:
    with database.session_factory() as session:
        users = {}
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
        session.commit()
    app.state.database = database
    with database.session_factory() as session:
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        outsider_id = users["outsider"].id
        for actor, expected in (
            ("owner", 200),
            ("admin", 200),
            ("editor", 403),
            ("viewer", 403),
            ("outsider", 404),
            ("instance", 404),
        ):
            client.cookies.set("stashive_session", session_token(database, users[actor]))
            assert (
                await client.get(f"/api/collections/{collection_id}/members")
            ).status_code == expected
        client.cookies.set("stashive_session", session_token(database, users["owner"]))
        added = await client.post(
            f"/api/collections/{collection_id}/members",
            json={"username": "outsider", "role": "viewer"},
        )
        assert added.status_code == 201
        assert (
            await client.post(
                f"/api/collections/{collection_id}/members",
                json={"username": "outsider", "role": "viewer"},
            )
        ).status_code == 409
        changed = await client.patch(
            f"/api/collections/{collection_id}/members/{outsider_id}",
            json={"username": "ignored", "role": "editor"},
        )
        assert changed.status_code == 200
        client.cookies.set("stashive_session", session_token(database, users["editor"]))
        assert (
            await client.delete(f"/api/collections/{collection_id}/members/{outsider_id}")
        ).status_code == 403
        client.cookies.set("stashive_session", session_token(database, users["admin"]))
        assert (
            await client.delete(f"/api/collections/{collection_id}/members/{outsider_id}")
        ).status_code == 204
    with database.session_factory() as session:
        assert (
            session.scalar(
                select(CollectionMember).where(
                    CollectionMember.collection_id == collection_id,
                    CollectionMember.user_id == users["outsider"].id,
                )
            )
            is None
        )


@pytest.mark.anyio
async def test_member_list_legacy_and_not_found_are_hidden(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="hash")
        legacy = Collection(name="Legacy", type="movies")
        session.add_all([owner, legacy])
        session.commit()
        legacy_id = legacy.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        assert (await client.get(f"/api/collections/{legacy_id}/members")).status_code == 404
        assert (await client.get("/api/collections/999999/members")).status_code == 404


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor_role", "member_role"),
    [
        ("owner", "admin"),
        ("owner", "editor"),
        ("owner", "viewer"),
        ("admin", "admin"),
        ("admin", "editor"),
        ("admin", "viewer"),
    ],
)
async def test_member_add_allows_owner_and_admin_roles(
    database: Database, actor_role: str, member_role: str
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        admin = User(username="admin", password_hash="admin-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        session.add_all([owner, admin, target])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.flush()
        session.add(CollectionMember(collection_id=collection.id, user_id=admin.id, role="admin"))
        session.commit()
        collection_id, target_id = collection.id, target.id
        actor = owner if actor_role == "owner" else admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, actor))
        response = await client.post(
            f"/api/collections/{collection_id}/members",
            json={"username": " TARGET ", "role": member_role},
        )
        assert response.status_code == 201
        assert response.json() == {"username": "target", "role": member_role}
        members = await client.get(f"/api/collections/{collection_id}/members")
        assert members.status_code == 200
        assert {"username": "target", "role": member_role} in members.json()
        assert all(
            not {"password_hash", "csrf_token", "session_token", "setup_token"} & member.keys()
            for member in members.json()
        )
    with database.session_factory() as session:
        membership = session.scalar(
            select(CollectionMember).where(
                CollectionMember.collection_id == collection_id,
                CollectionMember.user_id == target_id,
            )
        )
        assert membership is not None
        assert membership.role == member_role


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor_role", "expected"),
    [
        ("editor", 403),
        ("viewer", 403),
        ("outsider", 404),
        ("instance", 404),
    ],
)
async def test_member_add_hides_or_forbids_unqualified_actors(
    database: Database, actor_role: str, expected: int
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        users = {}
        for name, instance_admin in (
            ("owner", False),
            ("editor", False),
            ("viewer", False),
            ("outsider", False),
            ("instance", True),
            ("target", False),
        ):
            user = User(
                username=name,
                password_hash=f"{name}-password-hash",
                is_instance_admin=instance_admin,
            )
            session.add(user)
            users[name] = user
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=users["owner"].id)
        session.add(collection)
        session.flush()
        session.add_all(
            [
                CollectionMember(
                    collection_id=collection.id, user_id=users["editor"].id, role="editor"
                ),
                CollectionMember(
                    collection_id=collection.id, user_id=users["viewer"].id, role="viewer"
                ),
            ]
        )
        session.commit()
        collection_id, target_id = collection.id, users["target"].id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, users[actor_role]))
        response = await client.post(
            f"/api/collections/{collection_id}/members",
            json={"username": "target", "role": "viewer"},
        )
    assert response.status_code == expected
    with database.session_factory() as session:
        assert (
            session.scalar(
                select(CollectionMember).where(
                    CollectionMember.collection_id == collection_id,
                    CollectionMember.user_id == target_id,
                )
            )
            is None
        )


@pytest.mark.anyio
async def test_member_add_hides_legacy_and_missing_collections(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        legacy = Collection(name="Legacy", type="movies")
        session.add_all([owner, target, legacy])
        session.commit()
        legacy_id, target_id = legacy.id, target.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        for collection_id in (legacy_id, 999999):
            response = await client.post(
                f"/api/collections/{collection_id}/members",
                json={"username": "target", "role": "viewer"},
            )
            assert response.status_code == 404
    with database.session_factory() as session:
        assert (
            session.scalar(select(CollectionMember).where(CollectionMember.user_id == target_id))
            is None
        )


@pytest.mark.anyio
async def test_member_add_rejects_duplicate_without_changing_existing_role(
    database: Database,
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
        collection_id, member_id = collection.id, member.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.post(
            f"/api/collections/{collection_id}/members",
            json={"username": "member", "role": "admin"},
        )
    assert response.status_code == 409
    with database.session_factory() as session:
        memberships = session.scalars(
            select(CollectionMember).where(
                CollectionMember.collection_id == collection_id,
                CollectionMember.user_id == member_id,
            )
        ).all()
        assert len(memberships) == 1
        assert memberships[0].role == "viewer"


@pytest.mark.anyio
async def test_member_add_rejects_owner_as_a_normal_member(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        session.add(owner)
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.commit()
        collection_id, owner_id = collection.id, owner.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.post(
            f"/api/collections/{collection_id}/members",
            json={"username": "owner", "role": "admin"},
        )
    assert response.status_code == 404
    with database.session_factory() as session:
        assert session.get(Collection, collection_id).owner_user_id == owner_id
        assert (
            session.scalar(
                select(CollectionMember).where(
                    CollectionMember.collection_id == collection_id,
                    CollectionMember.user_id == owner_id,
                )
            )
            is None
        )


@pytest.mark.anyio
async def test_member_add_rejects_invalid_role_without_persisting_membership(
    database: Database,
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        session.add_all([owner, target])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.commit()
        collection_id, target_id = collection.id, target.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.post(
            f"/api/collections/{collection_id}/members",
            json={"username": "target", "role": "manager"},
        )
    assert response.status_code == 422
    with database.session_factory() as session:
        assert (
            session.scalar(
                select(CollectionMember).where(
                    CollectionMember.collection_id == collection_id,
                    CollectionMember.user_id == target_id,
                )
            )
            is None
        )


@pytest.mark.anyio
async def test_member_add_rejects_unknown_user_without_exposing_secrets(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        collection = Collection(name="Shared", type="movies", owner=owner)
        session.add_all([owner, collection])
        session.commit()
        collection_id = collection.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.post(
            f"/api/collections/{collection_id}/members",
            json={"username": "missing", "role": "viewer"},
        )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor_role", "current_role", "new_role"),
    [
        ("owner", "viewer", "editor"),
        ("owner", "editor", "admin"),
        ("owner", "admin", "viewer"),
        ("admin", "viewer", "editor"),
        ("admin", "editor", "admin"),
        ("admin", "admin", "viewer"),
    ],
)
async def test_member_update_allows_owner_and_admin_role_changes(
    database: Database, actor_role: str, current_role: str, new_role: str
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        admin = User(username="admin", password_hash="admin-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        session.add_all([owner, admin, target])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.flush()
        session.add_all(
            [
                CollectionMember(collection_id=collection.id, user_id=admin.id, role="admin"),
                CollectionMember(collection_id=collection.id, user_id=target.id, role=current_role),
            ]
        )
        session.commit()
        collection_id, target_id = collection.id, target.id
        actor = owner if actor_role == "owner" else admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, actor))
        response = await client.patch(
            f"/api/collections/{collection_id}/members/{target_id}",
            json={"username": "ignored", "role": new_role},
        )
        assert response.status_code == 200
        assert response.json() == {"role": new_role}
        members = await client.get(f"/api/collections/{collection_id}/members")
        assert members.status_code == 200
        assert {"username": "target", "role": new_role} in members.json()
        assert all(
            not {"password_hash", "csrf_token", "session_token", "setup_token"} & member.keys()
            for member in members.json()
        )
    with database.session_factory() as session:
        memberships = session.scalars(
            select(CollectionMember).where(
                CollectionMember.collection_id == collection_id,
                CollectionMember.user_id == target_id,
            )
        ).all()
        assert len(memberships) == 1
        assert memberships[0].role == new_role


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("actor_role", "expected"),
    [
        ("editor", 403),
        ("viewer", 403),
        ("outsider", 404),
        ("instance", 404),
    ],
)
async def test_member_update_hides_or_forbids_unqualified_actors(
    database: Database, actor_role: str, expected: int
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        users = {}
        for name, instance_admin in (
            ("owner", False),
            ("editor", False),
            ("viewer", False),
            ("outsider", False),
            ("instance", True),
            ("target", False),
        ):
            user = User(
                username=name,
                password_hash=f"{name}-password-hash",
                is_instance_admin=instance_admin,
            )
            session.add(user)
            users[name] = user
        session.flush()
        collection = Collection(
            name="Shared", type="movies", description="Original", owner_user_id=users["owner"].id
        )
        session.add(collection)
        session.flush()
        session.add_all(
            [
                CollectionMember(
                    collection_id=collection.id, user_id=users["editor"].id, role="editor"
                ),
                CollectionMember(
                    collection_id=collection.id, user_id=users["viewer"].id, role="viewer"
                ),
                CollectionMember(
                    collection_id=collection.id, user_id=users["target"].id, role="viewer"
                ),
            ]
        )
        session.commit()
        collection_id, target_id = collection.id, users["target"].id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, users[actor_role]))
        response = await client.patch(
            f"/api/collections/{collection_id}/members/{target_id}",
            json={"username": "ignored", "role": "admin"},
        )
    assert response.status_code == expected
    with database.session_factory() as session:
        collection = session.get(Collection, collection_id)
        membership = session.scalar(
            select(CollectionMember).where(
                CollectionMember.collection_id == collection_id,
                CollectionMember.user_id == target_id,
            )
        )
        assert collection is not None
        assert collection.name == "Shared"
        assert collection.description == "Original"
        assert membership is not None
        assert membership.role == "viewer"
        memberships = session.scalars(
            select(CollectionMember).where(CollectionMember.collection_id == collection_id)
        ).all()
        assert {(item.user_id, item.role) for item in memberships} == {
            (users["editor"].id, "editor"),
            (users["viewer"].id, "viewer"),
            (target_id, "viewer"),
        }


@pytest.mark.anyio
@pytest.mark.parametrize("target_is_member", [True, False])
@pytest.mark.parametrize("actor_role", ["outsider", "instance"])
async def test_member_update_hides_target_details_from_non_members(
    database: Database, actor_role: str, target_is_member: bool
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        outsider = User(username="outsider", password_hash="outsider-password-hash")
        instance = User(
            username="instance", password_hash="instance-password-hash", is_instance_admin=True
        )
        session.add_all([owner, target, outsider, instance])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.flush()
        if target_is_member:
            session.add(
                CollectionMember(collection_id=collection.id, user_id=target.id, role="viewer")
            )
        session.commit()
        collection_id = collection.id
        target_id = target.id if target_is_member else 999999
        actor = outsider if actor_role == "outsider" else instance
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, actor))
        response = await client.patch(
            f"/api/collections/{collection_id}/members/{target_id}",
            json={"username": "ignored", "role": "admin"},
        )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_member_update_hides_legacy_and_missing_collections(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        legacy = Collection(name="Legacy", type="movies")
        session.add_all([owner, target, legacy])
        session.flush()
        session.add(CollectionMember(collection_id=legacy.id, user_id=target.id, role="viewer"))
        session.commit()
        legacy_id, target_id = legacy.id, target.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        for collection_id in (legacy_id, 999999):
            response = await client.patch(
                f"/api/collections/{collection_id}/members/{target_id}",
                json={"username": "ignored", "role": "admin"},
            )
            assert response.status_code == 404
    with database.session_factory() as session:
        membership = session.scalar(
            select(CollectionMember).where(
                CollectionMember.collection_id == legacy_id,
                CollectionMember.user_id == target_id,
            )
        )
        assert membership is not None
        assert membership.role == "viewer"


@pytest.mark.anyio
async def test_member_update_rejects_owner_target_without_creating_membership(
    database: Database,
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        session.add(owner)
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.commit()
        collection_id, owner_id = collection.id, owner.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.patch(
            f"/api/collections/{collection_id}/members/{owner_id}",
            json={"username": "ignored", "role": "viewer"},
        )
    assert response.status_code == 404
    with database.session_factory() as session:
        assert session.get(Collection, collection_id).owner_user_id == owner_id
        assert (
            session.scalar(
                select(CollectionMember).where(
                    CollectionMember.collection_id == collection_id,
                    CollectionMember.user_id == owner_id,
                )
            )
            is None
        )


@pytest.mark.anyio
async def test_member_update_rejects_non_member_without_implicit_creation(
    database: Database,
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        owner = User(username="owner", password_hash="owner-password-hash")
        target = User(username="target", password_hash="target-password-hash")
        session.add_all([owner, target])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.commit()
        collection_id, target_id = collection.id, target.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.patch(
            f"/api/collections/{collection_id}/members/{target_id}",
            json={"username": "ignored", "role": "admin"},
        )
    assert response.status_code == 404
    with database.session_factory() as session:
        assert (
            session.scalar(
                select(CollectionMember).where(
                    CollectionMember.collection_id == collection_id,
                    CollectionMember.user_id == target_id,
                )
            )
            is None
        )


@pytest.mark.anyio
async def test_member_update_rejects_invalid_role_without_changing_membership(
    database: Database,
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
        session.add(CollectionMember(collection_id=collection.id, user_id=target.id, role="viewer"))
        session.commit()
        collection_id, target_id = collection.id, target.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, owner))
        response = await client.patch(
            f"/api/collections/{collection_id}/members/{target_id}",
            json={"username": "ignored", "role": "manager"},
        )
    assert response.status_code == 422
    with database.session_factory() as session:
        membership = session.scalar(
            select(CollectionMember).where(
                CollectionMember.collection_id == collection_id,
                CollectionMember.user_id == target_id,
            )
        )
        assert membership is not None
        assert membership.role == "viewer"
