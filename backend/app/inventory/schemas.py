"""Validated data transfer objects for the generic inventory core."""

from datetime import date

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    """Input required to create a structural collection."""

    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=64)
    description: str | None = None


class CatalogEntryCreate(BaseModel):
    """Input required to create a title or work."""

    collection_id: int = Field(gt=0)
    display_title: str = Field(min_length=1, max_length=512)
    type: str = Field(min_length=1, max_length=64)
    sort_title: str | None = None
    notes: str | None = None


class EditionCreate(BaseModel):
    """Input required to create a concrete product edition."""

    catalog_entry_id: int = Field(gt=0)
    display_name: str = Field(min_length=1, max_length=512)
    release_date: date | None = None
    publisher: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=64)


class IdentifierCreate(BaseModel):
    """Input required to associate an identifier with an edition."""

    edition_id: int = Field(gt=0)
    type: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=255)
    source: str | None = Field(default=None, max_length=255)


class InventoryItemCreate(BaseModel):
    """Input required to create one owned physical copy."""

    edition_id: int = Field(gt=0)
    notes: str | None = None
    condition: str | None = Field(default=None, max_length=64)
