"""ACL policy tests for collection ownership and memberships."""

import pytest

from app.collections.policy import CollectionCapability, effective_role, permits
from app.db.models import Collection, CollectionMember, User


@pytest.mark.parametrize(
    ("role", "capability", "allowed"),
    [
        ("owner", CollectionCapability.DELETE_COLLECTION, True),
        ("admin", CollectionCapability.EDIT_COLLECTION, True),
        ("admin", CollectionCapability.DELETE_COLLECTION, False),
        ("editor", CollectionCapability.EDIT_CONTENT, True),
        ("editor", CollectionCapability.MANAGE_MEMBERS, False),
        ("viewer", CollectionCapability.VIEW, True),
        ("viewer", CollectionCapability.EDIT_COLLECTION, False),
    ],
)
def test_capability_matrix(role: str, capability: CollectionCapability, allowed: bool) -> None:
    assert permits(role, capability) is allowed


def test_legacy_ownerless_collection_has_no_effective_role() -> None:
    user = User(id=1, username="admin", password_hash="hash", is_instance_admin=True)
    collection = Collection(id=1, name="Legacy", type="movies", owner_user_id=None)
    assert effective_role(collection, user, None) is None


def test_instance_admin_has_no_collection_bypass() -> None:
    instance_admin = User(id=1, username="admin", password_hash="hash", is_instance_admin=True)
    owner = User(id=2, username="owner", password_hash="hash")
    collection = Collection(id=1, name="Private", type="movies", owner_user_id=owner.id)
    assert effective_role(collection, instance_admin, None) is None


def test_member_role_is_used_when_user_is_not_owner() -> None:
    owner = User(id=1, username="owner", password_hash="hash")
    member = User(id=2, username="viewer", password_hash="hash")
    collection = Collection(id=1, name="Shared", type="movies", owner_user_id=owner.id)
    membership = CollectionMember(collection_id=collection.id, user_id=member.id, role="viewer")
    assert effective_role(collection, member, membership) == "viewer"
