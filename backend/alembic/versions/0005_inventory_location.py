"""Add optional physical-copy location assignment.

Revision ID: 0005_inventory_location
Revises: 0004_location_tree
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_inventory_location"
down_revision: str | Sequence[str] | None = "0004_location_tree"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add optional location assignment to existing physical copies."""
    with op.batch_alter_table("inventory_items") as batch:
        batch.add_column(sa.Column("location_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_inventory_items_location_id",
            "locations",
            ["location_id"],
            ["id"],
        )
        batch.create_index("ix_inventory_items_location_id", ["location_id"])


def downgrade() -> None:
    """Remove optional location assignment from physical copies."""
    with op.batch_alter_table("inventory_items") as batch:
        batch.drop_index("ix_inventory_items_location_id")
        batch.drop_constraint("fk_inventory_items_location_id", type_="foreignkey")
        batch.drop_column("location_id")
