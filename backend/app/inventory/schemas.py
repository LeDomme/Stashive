"""Transport schemas for collection-scoped catalog, edition, and identifier APIs."""

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator


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
    media_format: str | None = Field(default=None, max_length=64)
    release_date: date | None = None
    publisher: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=64)


class EditionUpdateInput(BaseModel):
    """Partial input for a concrete edition."""

    display_name: str | None = Field(default=None, min_length=1, max_length=512)
    media_format: str | None = Field(default=None, max_length=64)
    release_date: date | None = None
    publisher: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=64)


class EditionResponse(BaseModel):
    """Safe representation of a concrete edition."""

    id: int
    catalog_entry_id: int
    display_name: str
    media_format: str | None
    release_date: date | None
    publisher: str | None
    region: str | None
    language: str | None

    model_config = {"from_attributes": True}


class LibraryTitleSummary(BaseModel):
    id: int
    catalog_entry_id: int
    display_title: str
    sort_title: str | None
    type: str
    edition_count: int
    copy_count: int
    media_formats: list[str]


class LibraryTitleSearchResult(LibraryTitleSummary):
    """Compact title context for the Add item title picker."""


class AddItemTitleChoice(BaseModel):
    existing_id: int | None = Field(default=None, gt=0)
    new: CatalogEntryCreateInput | None = None

    @model_validator(mode="after")
    def exactly_one_choice(self) -> "AddItemTitleChoice":
        if (self.existing_id is None) == (self.new is None):
            raise ValueError("Choose exactly one of existing_id or new")
        return self


class AddItemEditionChoice(BaseModel):
    existing_id: int | None = Field(default=None, gt=0)
    new: EditionCreateInput | None = None

    @model_validator(mode="after")
    def exactly_one_choice(self) -> "AddItemEditionChoice":
        if (self.existing_id is None) == (self.new is None):
            raise ValueError("Choose exactly one of existing_id or new")
        return self


class AddItemCopyInput(BaseModel):
    condition: str | None = Field(default=None, max_length=64)
    notes: str | None = None
    location_id: int | None = Field(default=None, gt=0)


class AddItemInput(BaseModel):
    title: AddItemTitleChoice
    edition: AddItemEditionChoice
    copy_data: AddItemCopyInput

    @model_validator(mode="before")
    @classmethod
    def accept_copy_transport_field(cls, value: object) -> object:
        if isinstance(value, dict) and "copy" in value:
            return {**value, "copy_data": value["copy"]}
        return value


class AddItemResponse(BaseModel):
    catalog_entry_id: int
    edition_id: int
    inventory_item_id: int


class LibraryEdition(EditionResponse):
    identifiers: list["IdentifierResponse"]
    copies: list["InventoryItemResponse"]


class LibraryTitleDetail(BaseModel):
    catalog_entry: CatalogEntryResponse
    editions: list[LibraryEdition]


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
    location_id: int | None = Field(default=None, gt=0)


class InventoryItemUpdateInput(BaseModel):
    """Partial input for a physical copy and its optional location."""

    notes: str | None = None
    condition: str | None = Field(default=None, max_length=64)
    location_id: int | None = Field(default=None, gt=0)


class InventoryItemResponse(BaseModel):
    """Safe flat representation of one physical copy."""

    id: int
    edition_id: int
    condition: str | None
    notes: str | None
    location_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
