"""Central collection capability policy."""

from enum import StrEnum

from app.db.models import Collection, CollectionMember, User


class CollectionCapability(StrEnum):
    """Collection operations guarded by one reusable authorization policy."""

    VIEW = "view"
    EDIT_COLLECTION = "edit_collection"
    EDIT_CONTENT = "edit_content"
    MANAGE_MEMBERS = "manage_members"
    DELETE_COLLECTION = "delete_collection"
    TRANSFER_OWNERSHIP = "transfer_ownership"


ROLE_CAPABILITIES: dict[str, set[CollectionCapability]] = {
    "owner": set(CollectionCapability),
    "admin": {
        CollectionCapability.VIEW,
        CollectionCapability.EDIT_COLLECTION,
        CollectionCapability.EDIT_CONTENT,
        CollectionCapability.MANAGE_MEMBERS,
    },
    "editor": {CollectionCapability.VIEW, CollectionCapability.EDIT_CONTENT},
    "viewer": {CollectionCapability.VIEW},
}


def effective_role(
    collection: Collection,
    user: User,
    membership: CollectionMember | None,
) -> str | None:
    """Return the collection-local role; instance admins receive no bypass."""
    if collection.owner_user_id is None:
        return None
    if collection.owner_user_id == user.id:
        return "owner"
    return membership.role if membership else None


def permits(role: str | None, capability: CollectionCapability) -> bool:
    """Return whether a collection-local role allows a capability."""
    return role is not None and capability in ROLE_CAPABILITIES[role]
