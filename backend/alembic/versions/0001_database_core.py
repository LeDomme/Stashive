"""Create generic collection and inventory core tables.

Revision ID: 0001_database_core
Revises:
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_database_core"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the generic collection, catalogue, edition, and inventory tables."""
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collections_type", "collections", ["type"], unique=False)

    op.create_table(
        "catalog_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("display_title", sa.String(length=512), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("sort_title", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catalog_entries_collection_id", "catalog_entries", ["collection_id"])
    op.create_index("ix_catalog_entries_type", "catalog_entries", ["type"])

    op.create_table(
        "editions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("catalog_entry_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["catalog_entry_id"], ["catalog_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_editions_catalog_entry_id", "editions", ["catalog_entry_id"])

    op.create_table(
        "identifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("edition_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "edition_id",
            "type",
            "value",
            name="uq_identifiers_edition_type_value",
        ),
    )
    op.create_index("ix_identifiers_edition_id", "identifiers", ["edition_id"])
    op.create_index("ix_identifiers_type_value", "identifiers", ["type", "value"])

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("edition_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("condition", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_items_edition_id", "inventory_items", ["edition_id"])


def downgrade() -> None:
    """Drop the generic inventory core tables in dependency order."""
    op.drop_index("ix_inventory_items_edition_id", table_name="inventory_items")
    op.drop_table("inventory_items")

    op.drop_index("ix_identifiers_type_value", table_name="identifiers")
    op.drop_index("ix_identifiers_edition_id", table_name="identifiers")
    op.drop_table("identifiers")

    op.drop_index("ix_editions_catalog_entry_id", table_name="editions")
    op.drop_table("editions")

    op.drop_index("ix_catalog_entries_type", table_name="catalog_entries")
    op.drop_index("ix_catalog_entries_collection_id", table_name="catalog_entries")
    op.drop_table("catalog_entries")

    op.drop_index("ix_collections_type", table_name="collections")
    op.drop_table("collections")
