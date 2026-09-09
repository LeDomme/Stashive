"""Domain operations and invariants for collection-scoped location trees."""

from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.db.models import Collection, Location

LOCATION_TYPES = frozenset({"room", "cabinet", "shelf", "box", "drawer", "other"})


class LocationHierarchyError(Exception):
    """Base class for location domain errors mapped by the API layer later."""


class CollectionNotFoundError(LocationHierarchyError):
    """Raised when an operation references a collection that does not exist."""


class LocationNotFoundError(LocationHierarchyError):
    """Raised when an operation references a location that does not exist."""


class ParentNotFoundError(LocationHierarchyError):
    """Raised when a requested parent location does not exist."""


class ParentCollectionMismatchError(LocationHierarchyError):
    """Raised when a parent belongs to another collection."""


class SelfParentError(LocationHierarchyError):
    """Raised when a location is assigned as its own parent."""


class LocationCycleError(LocationHierarchyError):
    """Raised when a move would create, or encounters, a hierarchy cycle."""


class LocationHasChildrenError(LocationHierarchyError):
    """Raised when trying to delete a non-leaf location."""


class InvalidLocationTypeError(LocationHierarchyError):
    """Raised when a location type is outside the supported portable values."""


class InvalidLocationNameError(LocationHierarchyError):
    """Raised when a location name is blank or exceeds the storage limit."""


class LocationHierarchyService:
    """Perform atomic location-tree mutations without coupling to HTTP or ACL concerns."""

    def create_location(
        self,
        session: DatabaseSession,
        *,
        collection_id: int,
        name: str,
        location_type: str,
        description: str | None = None,
        parent_id: int | None = None,
    ) -> Location:
        """Create either a root location or a child of a same-collection parent."""
        if session.get(Collection, collection_id) is None:
            raise CollectionNotFoundError
        parent = self._parent_or_none(session, parent_id)
        if parent is not None and parent.collection_id != collection_id:
            raise ParentCollectionMismatchError
        location = Location(
            collection_id=collection_id,
            parent_id=parent_id,
            name=self._validated_name(name),
            type=self._validated_type(location_type),
            description=self._normalized_description(description),
        )
        session.add(location)
        session.commit()
        session.refresh(location)
        return location

    def update_metadata(
        self,
        session: DatabaseSession,
        *,
        location_id: int,
        name: str,
        location_type: str,
        description: str | None,
    ) -> Location:
        """Replace a location's editable metadata without changing its tree position."""
        location = self._location_or_error(session, location_id)
        validated_name = self._validated_name(name)
        validated_type = self._validated_type(location_type)
        normalized_description = self._normalized_description(description)
        location.name = validated_name
        location.type = validated_type
        location.description = normalized_description
        session.commit()
        session.refresh(location)
        return location

    def reparent_location(
        self,
        session: DatabaseSession,
        *,
        location_id: int,
        parent_id: int | None,
    ) -> Location:
        """Move a location to a root or a valid same-collection parent atomically."""
        location = self._location_or_error(session, location_id)
        if parent_id is None:
            location.parent_id = None
        else:
            if parent_id == location.id:
                raise SelfParentError
            parent = self._parent_or_none(session, parent_id)
            assert parent is not None
            if parent.collection_id != location.collection_id:
                raise ParentCollectionMismatchError
            self._ensure_not_descendant(session, location, parent)
            location.parent_id = parent.id
        session.commit()
        session.refresh(location)
        return location

    def delete_location(self, session: DatabaseSession, *, location_id: int) -> None:
        """Delete a leaf only; collection deletion remains responsible for whole-tree removal."""
        location = self._location_or_error(session, location_id)
        has_children = session.scalar(
            select(Location.id).where(Location.parent_id == location.id).limit(1)
        )
        if has_children is not None:
            raise LocationHasChildrenError
        session.delete(location)
        session.commit()

    def _location_or_error(self, session: DatabaseSession, location_id: int) -> Location:
        location = session.get(Location, location_id)
        if location is None:
            raise LocationNotFoundError
        return location

    def _parent_or_none(self, session: DatabaseSession, parent_id: int | None) -> Location | None:
        if parent_id is None:
            return None
        parent = session.get(Location, parent_id)
        if parent is None:
            raise ParentNotFoundError
        return parent

    def _ensure_not_descendant(
        self, session: DatabaseSession, location: Location, proposed_parent: Location
    ) -> None:
        """Walk ancestors defensively so arbitrary-depth moves cannot form a cycle."""
        current: Location | None = proposed_parent
        visited: set[int] = set()
        while current is not None:
            if current.id == location.id:
                raise LocationCycleError
            if current.id in visited:
                raise LocationCycleError
            visited.add(current.id)
            current = (
                session.get(Location, current.parent_id) if current.parent_id is not None else None
            )

    def _validated_name(self, name: str) -> str:
        normalized = name.strip()
        if not normalized or len(normalized) > 255:
            raise InvalidLocationNameError
        return normalized

    def _validated_type(self, location_type: str) -> str:
        normalized = location_type.strip().lower()
        if normalized not in LOCATION_TYPES:
            raise InvalidLocationTypeError
        return normalized

    def _normalized_description(self, description: str | None) -> str | None:
        if description is None:
            return None
        normalized = description.strip()
        return normalized or None
