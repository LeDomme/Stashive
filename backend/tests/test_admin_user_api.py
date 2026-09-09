"""HTTP tests for instance-administrator local user management."""

import pytest
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.database import Database
from app.db.models import Collection, CollectionMember, Session, User
from app.main import app
from tests.test_collection_api import session_token

password_hasher = PasswordHasher()
SAFE_USER_FIELDS = {
    "id",
    "username",
    "display_name",
    "is_instance_admin",
    "is_active",
    "created_at",
}


def create_user(username: str, *, instance_admin: bool = False) -> User:
    """Return a persisted-model-ready local account with a known password."""
    return User(
        username=username,
        password_hash=password_hasher.hash("correct horse battery staple"),
        is_instance_admin=instance_admin,
    )


@pytest.mark.anyio
async def test_instance_admin_can_list_safe_local_users(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        admin = create_user("admin", instance_admin=True)
        member = create_user("member")
        session.add_all([admin, member])
        session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, admin))
        response = await client.get("/api/admin/users")
    assert response.status_code == 200
    assert [item["username"] for item in response.json()] == ["admin", "member"]
    assert all(set(item) == SAFE_USER_FIELDS for item in response.json())


@pytest.mark.anyio
@pytest.mark.parametrize(("authenticated", "expected"), [(False, 401), (True, 403)])
async def test_user_list_requires_instance_admin(
    database: Database, authenticated: bool, expected: int
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        user = create_user("user")
        session.add(user)
        session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if authenticated:
            client.cookies.set("stashive_session", session_token(database, user))
        response = await client.get("/api/admin/users")
    assert response.status_code == expected


@pytest.mark.anyio
async def test_instance_admin_creates_normalized_user_without_secret_response(
    database: Database,
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        admin = create_user("admin", instance_admin=True)
        session.add(admin)
        session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, admin))
        response = await client.post(
            "/api/admin/users",
            json={
                "username": "  NewUser  ",
                "display_name": " New User ",
                "password": "a sufficiently long initial password",
                "is_instance_admin": True,
            },
        )
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert response.json()["display_name"] == "New User"
    assert response.json()["is_instance_admin"] is True
    assert set(response.json()) == SAFE_USER_FIELDS
    with database.session_factory() as session:
        stored = session.scalar(select(User).where(User.username == "newuser"))
        assert stored is not None
        assert stored.password_hash != "a sufficiently long initial password"
        assert password_hasher.verify(stored.password_hash, "a sufficiently long initial password")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"username": "ADMIN", "password": "a sufficiently long password"}, 409),
        ({"username": "   ", "password": "a sufficiently long password"}, 422),
        ({"username": "other", "password": "short"}, 422),
    ],
)
async def test_user_create_rejects_duplicate_and_invalid_data(
    database: Database, payload: dict[str, str], expected: int
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        admin = create_user("admin", instance_admin=True)
        session.add(admin)
        session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, admin))
        response = await client.post("/api/admin/users", json=payload)
    assert response.status_code == expected
    with database.session_factory() as session:
        assert session.scalar(select(User).where(User.username == "other")) is None


@pytest.mark.anyio
async def test_instance_admin_can_update_display_name_and_admin_state(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        admin = create_user("admin", instance_admin=True)
        target = create_user("target")
        session.add_all([admin, target])
        session.commit()
        target_id = target.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, admin))
        promoted = await client.patch(
            f"/api/admin/users/{target_id}",
            json={"display_name": " Target User ", "is_instance_admin": True},
        )
        assert promoted.status_code == 200
        assert promoted.json()["display_name"] == "Target User"
        assert promoted.json()["is_instance_admin"] is True
        demoted = await client.patch(
            f"/api/admin/users/{target_id}", json={"is_instance_admin": False}
        )
    assert demoted.status_code == 200
    assert demoted.json()["is_instance_admin"] is False


@pytest.mark.anyio
@pytest.mark.parametrize("changes", [{"is_instance_admin": False}, {"is_active": False}])
async def test_last_active_instance_admin_cannot_be_demoted_or_disabled(
    database: Database, changes: dict[str, bool]
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        admin = create_user("admin", instance_admin=True)
        session.add(admin)
        session.commit()
        admin_id = admin.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, admin))
        response = await client.patch(f"/api/admin/users/{admin_id}", json=changes)
    assert response.status_code == 409
    with database.session_factory() as session:
        stored = session.get(User, admin_id)
        assert stored is not None
        assert stored.is_instance_admin is True
        assert stored.is_active is True


@pytest.mark.anyio
async def test_password_reset_revokes_existing_sessions(database: Database) -> None:
    app.state.database = database
    with database.session_factory() as session:
        admin = create_user("admin", instance_admin=True)
        target = create_user("target")
        session.add_all([admin, target])
        session.commit()
        target_id = target.id
    old_target_token = session_token(database, target)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, admin))
        response = await client.post(
            f"/api/admin/users/{target_id}/password",
            json={"password": "a brand new sufficiently long password"},
        )
        assert response.status_code == 200
        assert set(response.json()) == SAFE_USER_FIELDS
        client.cookies.set("stashive_session", old_target_token)
        assert (await client.get("/api/auth/me")).status_code == 401
        assert (
            await client.post(
                "/api/auth/login",
                json={"username": "target", "password": "correct horse battery staple"},
            )
        ).status_code == 401
        assert (
            await client.post(
                "/api/auth/login",
                json={"username": "target", "password": "a brand new sufficiently long password"},
            )
        ).status_code == 200
    with database.session_factory() as session:
        assert (
            session.scalar(select(Session.revoked_at).where(Session.user_id == target_id))
            is not None
        )


@pytest.mark.anyio
async def test_disable_revokes_sessions_preserves_memberships_and_enable_allows_login(
    database: Database,
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        admin = create_user("admin", instance_admin=True)
        owner = create_user("owner")
        target = create_user("target")
        session.add_all([admin, owner, target])
        session.flush()
        collection = Collection(name="Shared", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.flush()
        session.add(CollectionMember(collection_id=collection.id, user_id=target.id, role="viewer"))
        session.commit()
        target_id, collection_id = target.id, collection.id
    target_token = session_token(database, target)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, admin))
        disabled = await client.patch(f"/api/admin/users/{target_id}", json={"is_active": False})
        assert disabled.status_code == 200
        assert disabled.json()["is_active"] is False
        client.cookies.set("stashive_session", target_token)
        assert (await client.get("/api/auth/me")).status_code == 401
        assert (
            await client.post(
                "/api/auth/login",
                json={"username": "target", "password": "correct horse battery staple"},
            )
        ).status_code == 401
        client.cookies.set("stashive_session", session_token(database, admin))
        enabled = await client.patch(f"/api/admin/users/{target_id}", json={"is_active": True})
        assert enabled.status_code == 200
        assert enabled.json()["is_active"] is True
        assert (
            await client.post(
                "/api/auth/login",
                json={"username": "target", "password": "correct horse battery staple"},
            )
        ).status_code == 200
    with database.session_factory() as session:
        membership = session.scalar(
            select(CollectionMember).where(
                CollectionMember.collection_id == collection_id,
                CollectionMember.user_id == target_id,
            )
        )
        assert membership is not None
        assert membership.role == "viewer"


@pytest.mark.anyio
async def test_instance_admin_user_management_does_not_grant_collection_access(
    database: Database,
) -> None:
    app.state.database = database
    with database.session_factory() as session:
        instance_admin = create_user("instance-admin", instance_admin=True)
        owner = create_user("owner")
        target = create_user("target")
        session.add_all([instance_admin, owner, target])
        session.flush()
        collection = Collection(name="Private", type="movies", owner_user_id=owner.id)
        session.add(collection)
        session.commit()
        collection_id = collection.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("stashive_session", session_token(database, instance_admin))
        assert (await client.get("/api/admin/users")).status_code == 200
        assert (await client.get(f"/api/collections/{collection_id}")).status_code == 404
