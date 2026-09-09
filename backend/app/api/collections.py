"""Collection CRUD with central collection-local authorization."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DatabaseSession

from app.api.auth import current_user_or_401, get_session
from app.collections.policy import CollectionCapability, effective_role, permits
from app.db.models import Collection, CollectionMember, User

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=64)
    description: str | None = None


class MemberInput(BaseModel):
    username: str = Field(min_length=1)
    role: str = Field(pattern="^(admin|editor|viewer)$")


class OwnershipTransferInput(BaseModel):
    username: str = Field(min_length=1)


def collection_or_404(
    session: DatabaseSession, user: User, collection_id: int
) -> tuple[Collection, str]:
    collection = session.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    membership = session.scalar(
        select(CollectionMember).where(
            CollectionMember.collection_id == collection.id, CollectionMember.user_id == user.id
        )
    )
    role = effective_role(collection, user, membership)
    if not permits(role, CollectionCapability.VIEW):
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection, role


@router.get("")
def list_collections(
    session: DatabaseSession = Depends(get_session), user: User = Depends(current_user_or_401)
) -> list[dict[str, object]]:
    rows = session.execute(
        select(Collection, CollectionMember.role)
        .outerjoin(
            CollectionMember,
            (CollectionMember.collection_id == Collection.id)
            & (CollectionMember.user_id == user.id),
        )
        .where(or_(Collection.owner_user_id == user.id, CollectionMember.user_id == user.id))
    ).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "type": item.type,
            "description": item.description,
            "role": "owner" if item.owner_user_id == user.id else role,
        }
        for item, role in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> dict[str, object]:
    collection = Collection(owner_user_id=user.id, **payload.model_dump())
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return {"id": collection.id, "name": collection.name, "role": "owner"}


@router.get("/{collection_id}")
def get_collection(
    collection_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> dict[str, object]:
    collection, role = collection_or_404(session, user, collection_id)
    return {
        "id": collection.id,
        "name": collection.name,
        "type": collection.type,
        "description": collection.description,
        "role": role,
    }


@router.patch("/{collection_id}")
def update_collection(
    collection_id: int,
    payload: CollectionInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> dict[str, object]:
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.EDIT_COLLECTION):
        raise HTTPException(status_code=403, detail="Collection editing is not permitted")
    for field, value in payload.model_dump().items():
        setattr(collection, field, value)
    session.commit()
    return {"id": collection.id, "name": collection.name, "role": role}


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> None:
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.DELETE_COLLECTION):
        raise HTTPException(status_code=403, detail="Collection deletion is not permitted")
    session.delete(collection)
    session.commit()


@router.get("/{collection_id}/members")
def list_members(
    collection_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> list[dict[str, object]]:
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.MANAGE_MEMBERS):
        raise HTTPException(status_code=403, detail="Member management is not permitted")
    rows = session.execute(
        select(CollectionMember, User)
        .join(User)
        .where(CollectionMember.collection_id == collection.id)
    ).all()
    return [{"username": member_user.username, "role": member.role} for member, member_user in rows]


@router.post("/{collection_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    collection_id: int,
    payload: MemberInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> dict[str, str]:
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.MANAGE_MEMBERS):
        raise HTTPException(status_code=403, detail="Member management is not permitted")
    target = session.scalar(
        select(User).where(User.username == payload.username.strip().casefold())
    )
    if target is None or target.id == collection.owner_user_id:
        raise HTTPException(status_code=404, detail="User not found")
    if session.scalar(
        select(CollectionMember).where(
            CollectionMember.collection_id == collection.id, CollectionMember.user_id == target.id
        )
    ):
        raise HTTPException(status_code=409, detail="User is already a member")
    session.add(CollectionMember(collection_id=collection.id, user_id=target.id, role=payload.role))
    session.commit()
    return {"username": target.username, "role": payload.role}


@router.patch("/{collection_id}/members/{user_id}")
def update_member(
    collection_id: int,
    user_id: int,
    payload: MemberInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> dict[str, str]:
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.MANAGE_MEMBERS):
        raise HTTPException(status_code=403, detail="Member management is not permitted")
    member = session.scalar(
        select(CollectionMember).where(
            CollectionMember.collection_id == collection.id, CollectionMember.user_id == user_id
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = payload.role
    session.commit()
    return {"role": member.role}


@router.delete("/{collection_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    collection_id: int,
    user_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> None:
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.MANAGE_MEMBERS):
        raise HTTPException(status_code=403, detail="Member management is not permitted")
    member = session.scalar(
        select(CollectionMember).where(
            CollectionMember.collection_id == collection.id, CollectionMember.user_id == user_id
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    session.delete(member)
    session.commit()


@router.post("/{collection_id}/transfer-ownership")
def transfer_ownership(
    collection_id: int,
    payload: OwnershipTransferInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> dict[str, str]:
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.TRANSFER_OWNERSHIP):
        raise HTTPException(status_code=403, detail="Ownership transfer is not permitted")
    target = session.scalar(
        select(User).where(User.username == payload.username.strip().casefold())
    )
    if target is None or target.id == user.id:
        raise HTTPException(status_code=404, detail="User not found")
    target_member = session.scalar(
        select(CollectionMember).where(
            CollectionMember.collection_id == collection.id, CollectionMember.user_id == target.id
        )
    )
    if target_member is not None:
        session.delete(target_member)
    collection.owner_user_id = target.id
    session.add(CollectionMember(collection_id=collection.id, user_id=user.id, role="admin"))
    session.commit()
    return {"owner": target.username}
