"""Transport schemas for the collection-scoped location API."""

from typing import Self

from pydantic import BaseModel, Field, field_validator

from app.locations.service import LOCATION_TYPES


class LocationCreateInput(BaseModel):
    """Input for creating a root or child location."""

    name: str = Field(min_length=1, max_length=255)
    type: str
    description: str | None = None
    parent_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only names before invoking the domain service."""
        if not value.strip():
            raise ValueError("Name must not be blank")
        return value

    @field_validator("type")
    @classmethod
    def type_must_be_supported(cls, value: str) -> str:
        """Normalize and validate the portable set of location types."""
        normalized = value.strip().lower()
        if normalized not in LOCATION_TYPES:
            raise ValueError("Unsupported location type")
        return normalized


class LocationUpdateInput(BaseModel):
    """Partial input for metadata changes and reparenting."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = None
    description: str | None = None
    parent_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        """Reject whitespace-only supplied names while allowing omitted fields."""
        if value is not None and not value.strip():
            raise ValueError("Name must not be blank")
        return value

    @field_validator("type")
    @classmethod
    def type_must_be_supported(cls, value: str | None) -> str | None:
        """Normalize a supplied type and reject unknown values."""
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in LOCATION_TYPES:
            raise ValueError("Unsupported location type")
        return normalized


class LocationResponse(BaseModel):
    """Safe flat location response used for mutations."""

    id: int
    collection_id: int
    parent_id: int | None
    name: str
    type: str
    description: str | None

    model_config = {"from_attributes": True}


class LocationTreeResponse(LocationResponse):
    """A location node and its recursively nested child nodes."""

    children: list[Self] = Field(default_factory=list)
