"""proxy bidding: high_bidder_max, max_amount, is_proxy

Revision ID: 202607170010
Revises: 202607170009
Create Date: 2026-07-17 00:10:00.000000

Proxy bidding uchun maydonlar:
- auctions.high_bidder_max — leader to'lashga tayyor maksimal summa (yashirin).
- bids.max_amount — bidder max'i (yashirin). Mavjud qatorlar uchun = amount.
- bids.is_proxy — yozuv tizim tomonidan avtomatik ko'tarilganmi.

max_amount NOT NULL: avval nullable qo'shiladi, amount bilan to'ldiriladi,
keyin NOT NULL qilinadi (mavjud bidlar uchun max = ko'ringan bid).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607170010"
down_revision: str | None = "202607170009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("auctions", sa.Column("high_bidder_max", sa.BigInteger(), nullable=True))

    op.add_column("bids", sa.Column("max_amount", sa.BigInteger(), nullable=True))
    op.add_column(
        "bids",
        sa.Column("is_proxy", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Mavjud bidlar: max = ko'ringan bid (proxy o'chiq bo'lgan).
    op.execute("UPDATE bids SET max_amount = amount WHERE max_amount IS NULL")
    op.alter_column("bids", "max_amount", nullable=False)
    # server_default faqat backfill uchun kerak edi — modelda default yo'q.
    op.alter_column("bids", "is_proxy", server_default=None)

    # DB darajasidagi himoya: max >= ko'ringan bid.
    op.create_check_constraint("ck_bids_max_ge_amount", "bids", "max_amount >= amount")


def downgrade() -> None:
    op.drop_constraint("ck_bids_max_ge_amount", "bids", type_="check")
    op.drop_column("bids", "is_proxy")
    op.drop_column("bids", "max_amount")
    op.drop_column("auctions", "high_bidder_max")
