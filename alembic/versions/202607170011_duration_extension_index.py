"""auksion: duration_days, extension_count + bids kompozit index

Revision ID: 202607170011
Revises: 202607170010
Create Date: 2026-07-17 00:11:00.000000

- auctions.duration_days (SMALLINT, nullable) — 3/5/7 kun; berilsa
  end_time = start_time + duration_days. Nullable: end_time bilan
  yaratilgan auksionlar uchun (orqaga moslik).
- auctions.extension_count (INT, default 0) — anti-sniping necha marta
  uzaytirgani. Cheksiz cho'zilishning oldini olish uchun.
- ix_bids_auction_amount_created — g'olib bidni tez topish.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607170011"
down_revision: str | None = "202607170010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("auctions", sa.Column("duration_days", sa.SmallInteger(), nullable=True))
    op.add_column(
        "auctions",
        sa.Column("extension_count", sa.Integer(), nullable=False, server_default="0"),
    )
    # server_default faqat mavjud qatorlar uchun edi — modelda default yo'q.
    op.alter_column("auctions", "extension_count", server_default=None)

    # duration_days berilsa 3/5/7 bo'lishi shart (DB darajasida ham).
    op.create_check_constraint(
        "ck_auctions_duration_days",
        "auctions",
        "duration_days IS NULL OR duration_days IN (3, 5, 7)",
    )

    op.create_index(
        "ix_bids_auction_amount_created",
        "bids",
        ["auction_id", "amount", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_bids_auction_amount_created", table_name="bids")
    op.drop_constraint("ck_auctions_duration_days", "auctions", type_="check")
    op.drop_column("auctions", "extension_count")
    op.drop_column("auctions", "duration_days")
