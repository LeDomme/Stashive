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
