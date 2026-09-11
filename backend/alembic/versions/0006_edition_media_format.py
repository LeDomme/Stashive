"""Add nullable media format to editions.

Revision ID: 0006_edition_media_format
Revises: 0005_inventory_location
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_edition_media_format"
down_revision: str | Sequence[str] | None = "0005_inventory_location"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("editions", sa.Column("media_format", sa.String(length=64), nullable=True))

def downgrade() -> None:
    op.drop_column("editions", "media_format")
