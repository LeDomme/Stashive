"""Add collection ownership and member access control.

Revision ID: 0003_collections_acl
Revises: 0002_local_authentication
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_collections_acl"
down_revision: str | Sequence[str] | None = "0002_local_authentication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("collections") as batch:
        batch.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_collections_owner_user_id",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_collections_owner_user_id", ["owner_user_id"])
    op.create_table(
        "collection_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "user_id", name="uq_collection_members_user"),
    )
    op.create_index("ix_collection_members_collection_id", "collection_members", ["collection_id"])
    op.create_index("ix_collection_members_user_id", "collection_members", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_collection_members_user_id", table_name="collection_members")
    op.drop_index("ix_collection_members_collection_id", table_name="collection_members")
    op.drop_table("collection_members")
    with op.batch_alter_table("collections") as batch:
        batch.drop_index("ix_collections_owner_user_id")
        batch.drop_constraint("fk_collections_owner_user_id", type_="foreignkey")
        batch.drop_column("owner_user_id")
