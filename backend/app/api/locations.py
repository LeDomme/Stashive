"""Collection-scoped location tree endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.api.auth import current_user_or_401, current_user_with_csrf_or_403, get_session
from app.api.collections import collection_or_404
from app.collections.policy import CollectionCapability, permits
from app.db.models import Collection, Location, User
from app.locations.schemas import (
    LocationCreateInput,
    LocationResponse,
    LocationTreeResponse,
    LocationUpdateInput,
)
from app.locations.service import (
    CollectionNotFoundError,
    InvalidLocationNameError,
    InvalidLocationTypeError,
    LocationCycleError,
    LocationHasChildrenError,
    LocationHasInventoryItemsError,
    LocationHierarchyError,
    LocationHierarchyService,
    LocationNotFoundError,
    ParentCollectionMismatchError,
    ParentNotFoundError,
    SelfParentError,
)

router = APIRouter(prefix="/collections", tags=["locations"])


def editable_collection_or_403(
    session: DatabaseSession, user: User, collection_id: int
) -> Collection:
    """Resolve a visible collection and require the shared content-edit capability."""
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.EDIT_CONTENT):
        raise HTTPException(status_code=403, detail="Location editing is not permitted")
    return collection


def location_in_collection_or_404(
    session: DatabaseSession, collection: Collection, location_id: int
) -> Location:
    """Resolve a location only inside a collection to avoid cross-collection existence leaks."""
    location = session.scalar(
        select(Location).where(Location.id == location_id, Location.collection_id == collection.id)
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


def location_error_to_http(error: LocationHierarchyError) -> HTTPException:
    """Map domain failures to safe, stable location API responses."""
    if isinstance(error, (CollectionNotFoundError, LocationNotFoundError)):
        return HTTPException(status_code=404, detail="Location not found")
    if isinstance(error, (ParentNotFoundError, ParentCollectionMismatchError)):
        return HTTPException(status_code=404, detail="Parent location not found")
    if isinstance(error, (SelfParentError, LocationCycleError)):
        return HTTPException(status_code=409, detail="Location move would create a cycle")
    if isinstance(error, LocationHasChildrenError):
        return HTTPException(status_code=409, detail="Location has child locations")
    if isinstance(error, LocationHasInventoryItemsError):
        return HTTPException(status_code=409, detail="Location has assigned inventory items")
    if isinstance(error, (InvalidLocationNameError, InvalidLocationTypeError)):
        return HTTPException(status_code=422, detail="Invalid location input")
    raise error


def build_location_tree(locations: list[Location]) -> list[LocationTreeResponse]:
    """Build a deterministically ordered tree without extra queries or recursive traversal."""
    nodes = {
        location.id: LocationTreeResponse(
            id=location.id,
            collection_id=location.collection_id,
            parent_id=location.parent_id,
            name=location.name,
            type=location.type,
            description=location.description,
        )
        for location in locations
    }
    parent_ids = {location.id: location.parent_id for location in locations}

    def has_acyclic_parent_chain(location_id: int) -> bool:
        current_id = parent_ids[location_id]
        visited = {location_id}
        while current_id is not None:
            if current_id in visited or current_id not in parent_ids:
                return False
            visited.add(current_id)
            current_id = parent_ids[current_id]
        return True

    roots: list[LocationTreeResponse] = []
    for location in locations:
        node = nodes[location.id]
        if location.parent_id is None or not has_acyclic_parent_chain(location.id):
            roots.append(node)
        else:
            nodes[location.parent_id].children.append(node)
    return roots


@router.get("/{collection_id}/locations", response_model=list[LocationTreeResponse])
def list_location_tree(
    collection_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> list[LocationTreeResponse]:
    """Return a complete, name-then-id ordered location tree for a visible collection."""
    collection_or_404(session, user, collection_id)
    locations = list(
        session.scalars(
            select(Location)
            .where(Location.collection_id == collection_id)
            .order_by(func.lower(Location.name), Location.id)
        )
    )
    return build_location_tree(locations)


@router.post(
    "/{collection_id}/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_location(
    collection_id: int,
    payload: LocationCreateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> Location:
    """Create a root or same-collection child location."""
    editable_collection_or_403(session, user, collection_id)
    try:
        return LocationHierarchyService().create_location(
            session,
            collection_id=collection_id,
            name=payload.name,
            location_type=payload.type,
            description=payload.description,
            parent_id=payload.parent_id,
        )
    except LocationHierarchyError as error:
        raise location_error_to_http(error) from error


@router.patch("/{collection_id}/locations/{location_id}", response_model=LocationResponse)
def update_location(
    collection_id: int,
    location_id: int,
    payload: LocationUpdateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> Location:
    """Apply partial metadata and parent updates through the location hierarchy service."""
    collection = editable_collection_or_403(session, user, collection_id)
    location = location_in_collection_or_404(session, collection, location_id)
    fields = payload.model_fields_set
    service = LocationHierarchyService()
    try:
        if "parent_id" in fields:
            location = service.reparent_location(
                session, location_id=location.id, parent_id=payload.parent_id
            )
        if {"name", "type", "description"} & fields:
            location = service.update_metadata(
                session,
                location_id=location.id,
                name=payload.name if "name" in fields else location.name,
                location_type=payload.type if "type" in fields else location.type,
                description=payload.description
                if "description" in fields
                else location.description,
            )
        return location
    except LocationHierarchyError as error:
        raise location_error_to_http(error) from error


@router.delete("/{collection_id}/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    collection_id: int,
    location_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> None:
    """Delete a leaf location while preserving the service's non-recursive rule."""
    collection = editable_collection_or_403(session, user, collection_id)
    location = location_in_collection_or_404(session, collection, location_id)
    try:
        LocationHierarchyService().delete_location(session, location_id=location.id)
    except LocationHierarchyError as error:
        raise location_error_to_http(error) from error
