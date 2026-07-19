"""reviews jadvali (ikki tomonlama sharh / sotuvchi reytingi)

Revision ID: 202607170015
Revises: 202607170014
Create Date: 2026-07-17 00:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607170015"
down_revision: str | None = "202607170014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("from_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("to_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stars", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("order_id", "from_id", name="uq_reviews_order_from"),
        sa.CheckConstraint("stars BETWEEN 1 AND 5", name="ck_reviews_stars_range"),
    )
    op.create_index("ix_reviews_id", "reviews", ["id"])
    op.create_index("ix_reviews_order_id", "reviews", ["order_id"])
    op.create_index("ix_reviews_from_id", "reviews", ["from_id"])
    op.create_index("ix_reviews_to_id", "reviews", ["to_id"])


def downgrade() -> None:
    op.drop_table("reviews")
