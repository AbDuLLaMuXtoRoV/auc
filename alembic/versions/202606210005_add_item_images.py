"""add item images

Revision ID: 202606210005
Revises: 202606210004
Create Date: 2026-06-21 00:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606210005"
down_revision: str | None = "202606210004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "item_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_images_id"), "item_images", ["id"], unique=False)
    op.create_index(op.f("ix_item_images_item_id"), "item_images", ["item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_item_images_item_id"), table_name="item_images")
    op.drop_index(op.f("ix_item_images_id"), table_name="item_images")
    op.drop_table("item_images")
