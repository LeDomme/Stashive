"""Transport schemas for collection-scoped catalog, edition, and identifier APIs."""

from datetime import date

from pydantic import BaseModel, Field, field_validator


class CatalogEntryCreateInput(BaseModel):
    """Input for creating a conceptual title within the path collection."""

    display_title: str = Field(min_length=1, max_length=512)
    type: str = Field(min_length=1, max_length=64)
    sort_title: str | None = Field(default=None, max_length=512)
    notes: str | None = None

    @field_validator("display_title")
    @classmethod
    def display_title_must_not_be_blank(cls, value: str) -> str:
        """Reject titles consisting only of whitespace."""
        if not value.strip():
            raise ValueError("Display title must not be blank")
        return value


class CatalogEntryUpdateInput(BaseModel):
    """Partial input for a conceptual title."""

    display_title: str | None = Field(default=None, min_length=1, max_length=512)
    type: str | None = Field(default=None, min_length=1, max_length=64)
    sort_title: str | None = Field(default=None, max_length=512)
    notes: str | None = None

    @field_validator("display_title")
    @classmethod
    def display_title_must_not_be_blank(cls, value: str | None) -> str | None:
        """Reject a supplied whitespace-only title while allowing omission."""
        if value is not None and not value.strip():
            raise ValueError("Display title must not be blank")
        return value


class CatalogEntryResponse(BaseModel):
    """Safe representation of a conceptual title."""

    id: int
    collection_id: int
    display_title: str
    type: str
    sort_title: str | None
    notes: str | None

    model_config = {"from_attributes": True}


class EditionCreateInput(BaseModel):
    """Input for creating a concrete edition below the path catalog entry."""

    display_name: str = Field(min_length=1, max_length=512)
    release_date: date | None = None
    publisher: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=64)


class EditionUpdateInput(BaseModel):
    """Partial input for a concrete edition."""

    display_name: str | None = Field(default=None, min_length=1, max_length=512)
    release_date: date | None = None
    publisher: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=64)


class EditionResponse(BaseModel):
    """Safe representation of a concrete edition."""

    id: int
    catalog_entry_id: int
    display_name: str
    release_date: date | None
    publisher: str | None
    region: str | None
    language: str | None

    model_config = {"from_attributes": True}


class IdentifierCreateInput(BaseModel):
    """Input for creating an identifier below the path edition."""

    type: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=255)
    source: str | None = Field(default=None, max_length=255)


class IdentifierUpdateInput(BaseModel):
    """Partial input for an edition-local identifier."""

    type: str | None = Field(default=None, min_length=1, max_length=64)
    value: str | None = Field(default=None, min_length=1, max_length=255)
    source: str | None = Field(default=None, max_length=255)


class IdentifierResponse(BaseModel):
    """Safe representation of an edition-local identifier."""

    id: int
    edition_id: int
    type: str
    value: str
    source: str | None

    model_config = {"from_attributes": True}


class InventoryItemCreate(BaseModel):
    """Domain input retained for the later physical-copy API step."""

    edition_id: int = Field(gt=0)
    notes: str | None = None
    condition: str | None = Field(default=None, max_length=64)
