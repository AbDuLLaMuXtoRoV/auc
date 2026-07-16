"""deepen auction bid rules

Revision ID: 202606210004
Revises: 202606210003
Create Date: 2026-06-21 00:04:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606210004"
down_revision: str | None = "202606210003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE item_status ADD VALUE IF NOT EXISTS 'SCHEDULED'")
    op.add_column("auctions", sa.Column("highest_bidder_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_auctions_highest_bidder_id_users",
        "auctions",
        "users",
        ["highest_bidder_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_auctions_highest_bidder_id"),
        "auctions",
        ["highest_bidder_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_auctions_highest_bidder_id"), table_name="auctions")
    op.drop_constraint("fk_auctions_highest_bidder_id_users", "auctions", type_="foreignkey")
    op.drop_column("auctions", "highest_bidder_id")
