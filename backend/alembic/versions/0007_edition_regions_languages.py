"""Structure edition regions and languages.

Revision ID: 0007_edition_regions_languages
Revises: 0006_edition_media_format
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_edition_regions_languages"
down_revision: str | Sequence[str] | None = "0006_edition_media_format"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "edition_regions",
        sa.Column("edition_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("edition_id", "value"),
    )
    op.create_table(
        "edition_languages",
        sa.Column("edition_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["edition_id"], ["editions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("edition_id", "value"),
    )
    op.execute(
        "INSERT INTO edition_regions (edition_id, value, position) "
        "SELECT id, region, 0 FROM editions WHERE region IS NOT NULL"
    )
    op.execute(
        "INSERT INTO edition_languages (edition_id, value, position) "
        "SELECT id, language, 0 FROM editions WHERE language IS NOT NULL"
    )
    with op.batch_alter_table("editions") as batch:
        batch.drop_column("region")
        batch.drop_column("language")


def downgrade() -> None:
    with op.batch_alter_table("editions") as batch:
        batch.add_column(sa.Column("region", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("language", sa.String(length=64), nullable=True))
    op.execute(
        "UPDATE editions SET region = (SELECT value FROM edition_regions "
        "WHERE edition_regions.edition_id = editions.id LIMIT 1)"
    )
    op.execute(
        "UPDATE editions SET language = (SELECT value FROM edition_languages "
        "WHERE edition_languages.edition_id = editions.id LIMIT 1)"
    )
    op.drop_table("edition_languages")
    op.drop_table("edition_regions")
