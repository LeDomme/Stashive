"""Persistent generic collection and inventory models."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampedModel:
    """Provide timestamps for persistent domain records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Collection(TimestampedModel, Base):
    """Structural collection root without access-control concerns."""

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped["User | None"] = relationship(back_populates="owned_collections")
    members: Mapped[list["CollectionMember"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan", passive_deletes=True
    )
    locations: Mapped[list["Location"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan", passive_deletes=True
    )

    catalog_entries: Mapped[list["CatalogEntry"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CatalogEntry(TimestampedModel, Base):
    """Represent a conceptual title or work in a collection."""

    __tablename__ = "catalog_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_title: Mapped[str] = mapped_column(String(512), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sort_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    collection: Mapped[Collection] = relationship(back_populates="catalog_entries")
    editions: Mapped[list["Edition"]] = relationship(
        back_populates="catalog_entry",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Edition(TimestampedModel, Base):
    """Represent one concrete product edition of a catalog entry."""

    __tablename__ = "editions"

    id: Mapped[int] = mapped_column(primary_key=True)
    catalog_entry_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)

    catalog_entry: Mapped[CatalogEntry] = relationship(back_populates="editions")
    identifiers: Mapped[list["Identifier"]] = relationship(
        back_populates="edition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        back_populates="edition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Identifier(TimestampedModel, Base):
    """Represent a portable identifier assigned to a concrete edition."""

    __tablename__ = "identifiers"
    __table_args__ = (
        UniqueConstraint("edition_id", "type", "value", name="uq_identifiers_edition_type_value"),
        Index("ix_identifiers_type_value", "type", "value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(
        ForeignKey("editions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    edition: Mapped[Edition] = relationship(back_populates="identifiers")


class InventoryItem(TimestampedModel, Base):
    """Represent one owned physical copy of an edition."""

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    edition_id: Mapped[int] = mapped_column(
        ForeignKey("editions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id"),
        nullable=True,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(64), nullable=True)

    edition: Mapped[Edition] = relationship(back_populates="inventory_items")
    location: Mapped["Location | None"] = relationship(back_populates="inventory_items")


class Location(TimestampedModel, Base):
    """Represent one collection-scoped node in a physical location tree."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    collection: Mapped[Collection] = relationship(back_populates="locations")
    parent: Mapped["Location | None"] = relationship(
        back_populates="children", remote_side="Location.id"
    )
    children: Mapped[list["Location"]] = relationship(
        back_populates="parent",
        passive_deletes=True,
    )
    inventory_items: Mapped[list[InventoryItem]] = relationship(back_populates="location")


class User(TimestampedModel, Base):
    """Represent a local Stashive account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_instance_admin: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    owned_collections: Mapped[list[Collection]] = relationship(back_populates="owner")
    collection_memberships: Mapped[list["CollectionMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class CollectionMember(TimestampedModel, Base):
    """Represent a non-owner collection membership."""

    __tablename__ = "collection_members"
    __table_args__ = (
        UniqueConstraint("collection_id", "user_id", name="uq_collection_members_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    collection: Mapped[Collection] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="collection_memberships")


class SetupToken(TimestampedModel, Base):
    """Represent a single-use, hashed first-run setup token."""

    __tablename__ = "setup_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Session(TimestampedModel, Base):
    """Represent a revocable server-side browser session."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
