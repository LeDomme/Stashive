"""Collection-scoped catalog, edition, and identifier endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DatabaseSession

from app.api.auth import current_user_or_401, current_user_with_csrf_or_403, get_session
from app.api.collections import collection_or_404
from app.collections.policy import CollectionCapability, permits
from app.db.models import (
    CatalogEntry,
    Collection,
    Edition,
    Identifier,
    InventoryItem,
    Location,
    User,
)
from app.inventory.schemas import (
    CatalogEntryCreateInput,
    CatalogEntryResponse,
    CatalogEntryUpdateInput,
    EditionCreateInput,
    EditionResponse,
    EditionUpdateInput,
    IdentifierCreateInput,
    IdentifierResponse,
    IdentifierUpdateInput,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdateInput,
)
from app.inventory.service import DuplicateIdentifierError, InventoryService

router = APIRouter(prefix="/collections", tags=["inventory"])


def editable_collection_or_403(
    session: DatabaseSession, user: User, collection_id: int
) -> Collection:
    """Resolve a visible collection and require the shared content-edit capability."""
    collection, role = collection_or_404(session, user, collection_id)
    if not permits(role, CollectionCapability.EDIT_CONTENT):
        raise HTTPException(status_code=403, detail="Inventory editing is not permitted")
    return collection


def entry_in_collection_or_404(
    session: DatabaseSession, collection: Collection, entry_id: int
) -> CatalogEntry:
    """Resolve a title only within the already visible collection."""
    entry = session.scalar(
        select(CatalogEntry).where(
            CatalogEntry.id == entry_id,
            CatalogEntry.collection_id == collection.id,
        )
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    return entry


def edition_in_collection_or_404(
    session: DatabaseSession, collection: Collection, edition_id: int
) -> Edition:
    """Resolve an edition only within the already visible collection."""
    edition = session.scalar(
        select(Edition)
        .join(Edition.catalog_entry)
        .where(Edition.id == edition_id, CatalogEntry.collection_id == collection.id)
    )
    if edition is None:
        raise HTTPException(status_code=404, detail="Edition not found")
    return edition


def identifier_in_edition_or_404(
    session: DatabaseSession, edition: Edition, identifier_id: int
) -> Identifier:
    """Resolve an identifier only within the already scoped edition."""
    identifier = session.scalar(
        select(Identifier).where(
            Identifier.id == identifier_id,
            Identifier.edition_id == edition.id,
        )
    )
    if identifier is None:
        raise HTTPException(status_code=404, detail="Identifier not found")
    return identifier


def identifier_error_to_http(error: DuplicateIdentifierError) -> HTTPException:
    """Map identifier uniqueness failures without exposing database details."""
    if isinstance(error, DuplicateIdentifierError):
        return HTTPException(status_code=409, detail="Identifier already exists for this edition")
    raise error


def location_in_collection_or_404(
    session: DatabaseSession, collection: Collection, location_id: int
) -> Location:
    """Resolve a location inside an already visible collection only."""
    location = session.scalar(
        select(Location).where(Location.id == location_id, Location.collection_id == collection.id)
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


def item_in_collection_or_404(
    session: DatabaseSession, collection: Collection, item_id: int
) -> InventoryItem:
    """Resolve a physical copy only in the requested collection."""
    item = session.scalar(
        select(InventoryItem)
        .join(InventoryItem.edition)
        .join(Edition.catalog_entry)
        .where(InventoryItem.id == item_id, CatalogEntry.collection_id == collection.id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.get("/{collection_id}/catalog-entries", response_model=list[CatalogEntryResponse])
def list_catalog_entries(
    collection_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> list[CatalogEntry]:
    """List titles in deterministic case-insensitive display order."""
    collection_or_404(session, user, collection_id)
    sort_key = func.lower(func.coalesce(CatalogEntry.sort_title, CatalogEntry.display_title))
    return list(
        session.scalars(
            select(CatalogEntry)
            .where(CatalogEntry.collection_id == collection_id)
            .order_by(sort_key, CatalogEntry.id)
        )
    )


@router.post(
    "/{collection_id}/catalog-entries",
    response_model=CatalogEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_catalog_entry(
    collection_id: int,
    payload: CatalogEntryCreateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> CatalogEntry:
    """Create a title in a collection the caller may edit."""
    editable_collection_or_403(session, user, collection_id)
    return InventoryService().create_catalog_entry(
        session,
        collection_id=collection_id,
        display_title=payload.display_title,
        entry_type=payload.type,
        sort_title=payload.sort_title,
        notes=payload.notes,
    )


@router.get("/{collection_id}/catalog-entries/{entry_id}", response_model=CatalogEntryResponse)
def get_catalog_entry(
    collection_id: int,
    entry_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> CatalogEntry:
    """Get one title without exposing entries from other collections."""
    collection, _ = collection_or_404(session, user, collection_id)
    return entry_in_collection_or_404(session, collection, entry_id)


@router.patch("/{collection_id}/catalog-entries/{entry_id}", response_model=CatalogEntryResponse)
def update_catalog_entry(
    collection_id: int,
    entry_id: int,
    payload: CatalogEntryUpdateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> CatalogEntry:
    """Apply a partial title update while preserving explicitly supplied nulls."""
    collection = editable_collection_or_403(session, user, collection_id)
    entry = entry_in_collection_or_404(session, collection, entry_id)
    fields = payload.model_fields_set
    return InventoryService().update_catalog_entry(
        session,
        entry_id=entry.id,
        display_title=payload.display_title if "display_title" in fields else entry.display_title,
        entry_type=payload.type if "type" in fields else entry.type,
        sort_title=payload.sort_title if "sort_title" in fields else entry.sort_title,
        notes=payload.notes if "notes" in fields else entry.notes,
    )


@router.delete(
    "/{collection_id}/catalog-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_catalog_entry(
    collection_id: int,
    entry_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> None:
    """Delete a title and its existing dependent data."""
    collection = editable_collection_or_403(session, user, collection_id)
    entry = entry_in_collection_or_404(session, collection, entry_id)
    InventoryService().delete_catalog_entry(session, entry_id=entry.id)


@router.get(
    "/{collection_id}/catalog-entries/{entry_id}/editions",
    response_model=list[EditionResponse],
)
def list_editions(
    collection_id: int,
    entry_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> list[Edition]:
    """List all editions of a title in stable identifier order."""
    collection, _ = collection_or_404(session, user, collection_id)
    entry_in_collection_or_404(session, collection, entry_id)
    return list(
        session.scalars(
            select(Edition).where(Edition.catalog_entry_id == entry_id).order_by(Edition.id)
        )
    )


@router.post(
    "/{collection_id}/catalog-entries/{entry_id}/editions",
    response_model=EditionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_edition(
    collection_id: int,
    entry_id: int,
    payload: EditionCreateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> Edition:
    """Create an edition beneath a title the caller may edit."""
    collection = editable_collection_or_403(session, user, collection_id)
    entry = entry_in_collection_or_404(session, collection, entry_id)
    return InventoryService().create_edition(
        session,
        catalog_entry_id=entry.id,
        display_name=payload.display_name,
        release_date=payload.release_date,
        publisher=payload.publisher,
        region=payload.region,
        language=payload.language,
    )


@router.get("/{collection_id}/editions/{edition_id}", response_model=EditionResponse)
def get_edition(
    collection_id: int,
    edition_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> Edition:
    """Get one edition without exposing editions from other collections."""
    collection, _ = collection_or_404(session, user, collection_id)
    return edition_in_collection_or_404(session, collection, edition_id)


@router.patch("/{collection_id}/editions/{edition_id}", response_model=EditionResponse)
def update_edition(
    collection_id: int,
    edition_id: int,
    payload: EditionUpdateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> Edition:
    """Apply a partial edition update while retaining supplied nullable-field intent."""
    collection = editable_collection_or_403(session, user, collection_id)
    edition = edition_in_collection_or_404(session, collection, edition_id)
    fields = payload.model_fields_set
    return InventoryService().update_edition(
        session,
        edition_id=edition.id,
        display_name=payload.display_name if "display_name" in fields else edition.display_name,
        release_date=payload.release_date if "release_date" in fields else edition.release_date,
        publisher=payload.publisher if "publisher" in fields else edition.publisher,
        region=payload.region if "region" in fields else edition.region,
        language=payload.language if "language" in fields else edition.language,
    )


@router.delete("/{collection_id}/editions/{edition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edition(
    collection_id: int,
    edition_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> None:
    """Delete an edition and its existing identifiers and physical copies."""
    collection = editable_collection_or_403(session, user, collection_id)
    edition = edition_in_collection_or_404(session, collection, edition_id)
    InventoryService().delete_edition(session, edition_id=edition.id)


@router.get(
    "/{collection_id}/editions/{edition_id}/identifiers",
    response_model=list[IdentifierResponse],
)
def list_identifiers(
    collection_id: int,
    edition_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> list[Identifier]:
    """List edition-local identifiers in stable identifier order."""
    collection, _ = collection_or_404(session, user, collection_id)
    edition = edition_in_collection_or_404(session, collection, edition_id)
    return list(
        session.scalars(
            select(Identifier).where(Identifier.edition_id == edition.id).order_by(Identifier.id)
        )
    )


@router.post(
    "/{collection_id}/editions/{edition_id}/identifiers",
    response_model=IdentifierResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_identifier(
    collection_id: int,
    edition_id: int,
    payload: IdentifierCreateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> Identifier:
    """Create an edition-local identifier."""
    collection = editable_collection_or_403(session, user, collection_id)
    edition = edition_in_collection_or_404(session, collection, edition_id)
    try:
        return InventoryService().create_identifier(
            session,
            edition_id=edition.id,
            identifier_type=payload.type,
            value=payload.value,
            source=payload.source,
        )
    except DuplicateIdentifierError as error:
        raise identifier_error_to_http(error) from error


@router.patch(
    "/{collection_id}/editions/{edition_id}/identifiers/{identifier_id}",
    response_model=IdentifierResponse,
)
def update_identifier(
    collection_id: int,
    edition_id: int,
    identifier_id: int,
    payload: IdentifierUpdateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> Identifier:
    """Apply a partial identifier update within a scoped edition."""
    collection = editable_collection_or_403(session, user, collection_id)
    edition = edition_in_collection_or_404(session, collection, edition_id)
    identifier = identifier_in_edition_or_404(session, edition, identifier_id)
    fields = payload.model_fields_set
    try:
        return InventoryService().update_identifier(
            session,
            identifier_id=identifier.id,
            identifier_type=payload.type if "type" in fields else identifier.type,
            value=payload.value if "value" in fields else identifier.value,
            source=payload.source if "source" in fields else identifier.source,
        )
    except DuplicateIdentifierError as error:
        raise identifier_error_to_http(error) from error


@router.delete(
    "/{collection_id}/editions/{edition_id}/identifiers/{identifier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_identifier(
    collection_id: int,
    edition_id: int,
    identifier_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> None:
    """Delete an identifier within its scoped edition."""
    collection = editable_collection_or_403(session, user, collection_id)
    edition = edition_in_collection_or_404(session, collection, edition_id)
    identifier = identifier_in_edition_or_404(session, edition, identifier_id)
    InventoryService().delete_identifier(session, identifier_id=identifier.id)


@router.get("/{collection_id}/inventory-items", response_model=list[InventoryItemResponse])
def list_inventory_items(
    collection_id: int,
    location_id: int | None = Query(default=None, gt=0),
    include_descendants: bool = True,
    unassigned: bool = False,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> list[InventoryItem]:
    """List copies with an optional scoped location or unassigned filter."""
    collection, _ = collection_or_404(session, user, collection_id)
    if location_id is not None and unassigned:
        raise HTTPException(status_code=422, detail="location_id and unassigned cannot be combined")
    if location_id is None and not include_descendants:
        raise HTTPException(status_code=422, detail="include_descendants requires location_id")
    if location_id is not None:
        location_in_collection_or_404(session, collection, location_id)
    return InventoryService().list_inventory(
        session,
        collection_id=collection.id,
        location_id=location_id,
        recursive=include_descendants,
        unassigned=unassigned,
    )


@router.post(
    "/{collection_id}/inventory-items",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_item(
    collection_id: int,
    payload: InventoryItemCreate,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> InventoryItem:
    """Create exactly one physical copy for an edition in this collection."""
    collection = editable_collection_or_403(session, user, collection_id)
    edition_in_collection_or_404(session, collection, payload.edition_id)
    if payload.location_id is not None:
        location_in_collection_or_404(session, collection, payload.location_id)
    return InventoryService().create_inventory_item(
        session,
        edition_id=payload.edition_id,
        condition=payload.condition,
        notes=payload.notes,
        location_id=payload.location_id,
    )


@router.get("/{collection_id}/inventory-items/{item_id}", response_model=InventoryItemResponse)
def get_inventory_item(
    collection_id: int,
    item_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_or_401),
) -> InventoryItem:
    """Get one physical copy without leaking cross-collection IDs."""
    collection, _ = collection_or_404(session, user, collection_id)
    return item_in_collection_or_404(session, collection, item_id)


@router.patch("/{collection_id}/inventory-items/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(
    collection_id: int,
    item_id: int,
    payload: InventoryItemUpdateInput,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> InventoryItem:
    """Partially update copy metadata and assign, move, or unassign its location."""
    collection = editable_collection_or_403(session, user, collection_id)
    item = item_in_collection_or_404(session, collection, item_id)
    fields = payload.model_fields_set
    service = InventoryService()
    if "location_id" in fields:
        if payload.location_id is not None:
            location_in_collection_or_404(session, collection, payload.location_id)
        item = service.move_inventory_item(
            session, item_id=item.id, location_id=payload.location_id
        )
    if {"condition", "notes"} & fields:
        item = service.update_inventory_item(
            session,
            item_id=item.id,
            condition=payload.condition if "condition" in fields else item.condition,
            notes=payload.notes if "notes" in fields else item.notes,
        )
    return item


@router.delete("/{collection_id}/inventory-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    collection_id: int,
    item_id: int,
    session: DatabaseSession = Depends(get_session),
    user: User = Depends(current_user_with_csrf_or_403),
) -> None:
    """Delete exactly one physical copy."""
    collection = editable_collection_or_403(session, user, collection_id)
    item = item_in_collection_or_404(session, collection, item_id)
    InventoryService().delete_inventory_item(session, item_id=item.id)
