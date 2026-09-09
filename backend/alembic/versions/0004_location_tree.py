"""Add collection-scoped hierarchical locations.

Revision ID: 0004_location_tree
Revises: 0003_collections_acl
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_location_tree"
down_revision: str | Sequence[str] | None = "0003_collections_acl"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the location tree with database cascades for full collection deletion."""
    # The service permits direct deletion only for leaves. CASCADE here deliberately lets a
    # collection-level database cascade remove every node in one operation.
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
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
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_collection_id", "locations", ["collection_id"])
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])


def downgrade() -> None:
    """Remove the location tree schema."""
    op.drop_index("ix_locations_parent_id", table_name="locations")
    op.drop_index("ix_locations_collection_id", table_name="locations")
    op.drop_table("locations")
