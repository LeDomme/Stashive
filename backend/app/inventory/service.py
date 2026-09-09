"""Collection-scoped domain operations for the generic inventory core."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DatabaseSession

from app.db.models import CatalogEntry, Collection, Edition, Identifier, InventoryItem, Location


class InventoryDomainError(Exception):
    """Base class for inventory domain errors mapped by an API layer later."""


class CollectionNotFoundError(InventoryDomainError):
    """Raised when an operation references a collection that does not exist."""


class CatalogEntryNotFoundError(InventoryDomainError):
    """Raised when an operation references a catalog entry that does not exist."""


class EditionNotFoundError(InventoryDomainError):
    """Raised when an operation references an edition that does not exist."""


class IdentifierNotFoundError(InventoryDomainError):
    """Raised when an operation references an identifier that does not exist."""


class InventoryItemNotFoundError(InventoryDomainError):
    """Raised when an operation references a physical copy that does not exist."""


class LocationNotFoundError(InventoryDomainError):
    """Raised when an operation references a location that does not exist."""


class CrossCollectionLocationAssignmentError(InventoryDomainError):
    """Raised when a physical copy is assigned to another collection's location."""


class DuplicateIdentifierError(InventoryDomainError):
    """Raised when an edition already has an identifier with matching type and value."""


class InventoryService:
    """Perform atomic generic catalog and physical-copy mutations."""

    def create_catalog_entry(
        self,
        session: DatabaseSession,
        *,
        collection_id: int,
        display_title: str,
        entry_type: str,
        sort_title: str | None = None,
        notes: str | None = None,
    ) -> CatalogEntry:
        """Create a conceptual title in an existing collection."""
        self._collection(session, collection_id)
        entry = CatalogEntry(
            collection_id=collection_id,
            display_title=display_title,
            type=entry_type,
            sort_title=sort_title,
            notes=notes,
        )
        session.add(entry)
        return self._commit_and_refresh(session, entry)

    def update_catalog_entry(
        self,
        session: DatabaseSession,
        *,
        entry_id: int,
        display_title: str,
        entry_type: str,
        sort_title: str | None,
        notes: str | None,
    ) -> CatalogEntry:
        """Replace the editable metadata of a conceptual title."""
        entry = self._entry(session, entry_id)
        entry.display_title = display_title
        entry.type = entry_type
        entry.sort_title = sort_title
        entry.notes = notes
        return self._commit_and_refresh(session, entry)

    def delete_catalog_entry(self, session: DatabaseSession, *, entry_id: int) -> None:
        """Delete a title and its dependent editions, identifiers, and physical copies."""
        session.delete(self._entry(session, entry_id))
        session.commit()

    def create_edition(
        self,
        session: DatabaseSession,
        *,
        catalog_entry_id: int,
        display_name: str,
        release_date: date | None = None,
        publisher: str | None = None,
        region: str | None = None,
        language: str | None = None,
    ) -> Edition:
        """Create a concrete product edition below an existing title."""
        self._entry(session, catalog_entry_id)
        edition = Edition(
            catalog_entry_id=catalog_entry_id,
            display_name=display_name,
            release_date=release_date,
            publisher=publisher,
            region=region,
            language=language,
        )
        session.add(edition)
        return self._commit_and_refresh(session, edition)

    def update_edition(
        self,
        session: DatabaseSession,
        *,
        edition_id: int,
        display_name: str,
        release_date: date | None,
        publisher: str | None,
        region: str | None,
        language: str | None,
    ) -> Edition:
        """Replace the editable metadata of a concrete product edition."""
        edition = self._edition(session, edition_id)
        edition.display_name = display_name
        edition.release_date = release_date
        edition.publisher = publisher
        edition.region = region
        edition.language = language
        return self._commit_and_refresh(session, edition)

    def delete_edition(self, session: DatabaseSession, *, edition_id: int) -> None:
        """Delete an edition and its dependent identifiers and physical copies."""
        session.delete(self._edition(session, edition_id))
        session.commit()

    def create_identifier(
        self,
        session: DatabaseSession,
        *,
        edition_id: int,
        identifier_type: str,
        value: str,
        source: str | None = None,
    ) -> Identifier:
        """Create an edition-local identifier."""
        self._edition(session, edition_id)
        identifier = Identifier(
            edition_id=edition_id,
            type=identifier_type,
            value=value,
            source=source,
        )
        session.add(identifier)
        return self._commit_identifier(session, identifier)

    def update_identifier(
        self,
        session: DatabaseSession,
        *,
        identifier_id: int,
        identifier_type: str,
        value: str,
        source: str | None,
    ) -> Identifier:
        """Replace an identifier's editable fields without moving it to another edition."""
        identifier = self._identifier(session, identifier_id)
        identifier.type = identifier_type
        identifier.value = value
        identifier.source = source
        return self._commit_identifier(session, identifier)

    def delete_identifier(self, session: DatabaseSession, *, identifier_id: int) -> None:
        """Delete one edition-local identifier."""
        session.delete(self._identifier(session, identifier_id))
        session.commit()

    def create_inventory_item(
        self,
        session: DatabaseSession,
        *,
        edition_id: int,
        condition: str | None = None,
        notes: str | None = None,
        location_id: int | None = None,
    ) -> InventoryItem:
        """Create exactly one physical copy, optionally assigned to a valid location."""
        edition = self._edition(session, edition_id)
        self._validate_location(session, edition, location_id)
        item = InventoryItem(
            edition_id=edition_id,
            condition=condition,
            notes=notes,
            location_id=location_id,
        )
        session.add(item)
        return self._commit_and_refresh(session, item)

    def update_inventory_item(
        self,
        session: DatabaseSession,
        *,
        item_id: int,
        condition: str | None,
        notes: str | None,
    ) -> InventoryItem:
        """Replace the editable condition and notes of one physical copy."""
        item = self._item(session, item_id)
        item.condition = condition
        item.notes = notes
        return self._commit_and_refresh(session, item)

    def move_inventory_item(
        self,
        session: DatabaseSession,
        *,
        item_id: int,
        location_id: int | None,
    ) -> InventoryItem:
        """Assign, move, or unassign a physical copy without recording move history."""
        item = self._item(session, item_id)
        self._validate_location(session, item.edition, location_id)
        if item.location_id != location_id:
            item.location_id = location_id
            return self._commit_and_refresh(session, item)
        return item

    def delete_inventory_item(self, session: DatabaseSession, *, item_id: int) -> None:
        """Delete exactly one physical copy."""
        session.delete(self._item(session, item_id))
        session.commit()

    def list_inventory(
        self,
        session: DatabaseSession,
        *,
        collection_id: int,
        location_id: int | None = None,
        recursive: bool = False,
        unassigned: bool = False,
    ) -> list[InventoryItem]:
        """List copies in a collection, with optional location or unassigned filtering."""
        self._collection(session, collection_id)
        query = (
            select(InventoryItem)
            .join(InventoryItem.edition)
            .join(Edition.catalog_entry)
            .where(CatalogEntry.collection_id == collection_id)
        )
        if unassigned:
            query = query.where(InventoryItem.location_id.is_(None))
        elif location_id is not None:
            location = self._location(session, location_id)
            if location.collection_id != collection_id:
                raise CrossCollectionLocationAssignmentError
            location_ids = {location.id}
            if recursive:
                location_ids.update(self._descendant_ids(session, location.id))
            query = query.where(InventoryItem.location_id.in_(location_ids))
        return list(session.scalars(query.order_by(InventoryItem.id)))

    def _collection(self, session: DatabaseSession, collection_id: int) -> Collection:
        collection = session.get(Collection, collection_id)
        if collection is None:
            raise CollectionNotFoundError
        return collection

    def _entry(self, session: DatabaseSession, entry_id: int) -> CatalogEntry:
        entry = session.get(CatalogEntry, entry_id)
        if entry is None:
            raise CatalogEntryNotFoundError
        return entry

    def _edition(self, session: DatabaseSession, edition_id: int) -> Edition:
        edition = session.get(Edition, edition_id)
        if edition is None:
            raise EditionNotFoundError
        return edition

    def _identifier(self, session: DatabaseSession, identifier_id: int) -> Identifier:
        identifier = session.get(Identifier, identifier_id)
        if identifier is None:
            raise IdentifierNotFoundError
        return identifier

    def _item(self, session: DatabaseSession, item_id: int) -> InventoryItem:
        item = session.get(InventoryItem, item_id)
        if item is None:
            raise InventoryItemNotFoundError
        return item

    def _location(self, session: DatabaseSession, location_id: int) -> Location:
        location = session.get(Location, location_id)
        if location is None:
            raise LocationNotFoundError
        return location

    def _validate_location(
        self,
        session: DatabaseSession,
        edition: Edition,
        location_id: int | None,
    ) -> None:
        if location_id is None:
            return
        location = self._location(session, location_id)
        if location.collection_id != edition.catalog_entry.collection_id:
            raise CrossCollectionLocationAssignmentError

    def _descendant_ids(self, session: DatabaseSession, location_id: int) -> set[int]:
        """Return every descendant by walking the collection-scoped adjacency tree."""
        descendants: set[int] = set()
        pending = [location_id]
        while pending:
            child_ids = session.scalars(
                select(Location.id).where(Location.parent_id.in_(pending))
            ).all()
            pending = [child_id for child_id in child_ids if child_id not in descendants]
            descendants.update(pending)
        return descendants

    def _commit_and_refresh[T](self, session: DatabaseSession, instance: T) -> T:
        session.commit()
        session.refresh(instance)
        return instance

    def _commit_identifier(self, session: DatabaseSession, identifier: Identifier) -> Identifier:
        try:
            return self._commit_and_refresh(session, identifier)
        except IntegrityError as error:
            session.rollback()
            raise DuplicateIdentifierError from error
