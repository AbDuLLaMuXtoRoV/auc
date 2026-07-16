"""pul: Numeric(12,2) so'm -> BIGINT tiyin

Revision ID: 202607170009
Revises: 202606210008
Create Date: 2026-07-17 00:00:00.000000

Nega:
- Numeric(12,2) UZS uchun tor edi — maksimum ~9 999 999 999.99 so'm.
- Pul = butun son (tiyin) qoidasi: yaxlitlash bitta joyda, taqqoslash aniq.

MUHIM: bu ma'lumot konvertatsiyasi, shunchaki tur o'zgarishi EMAS.
`USING (col * 100)::bigint` bo'lmasa 62 000.00 so'm -> 62 tiyin bo'lib
qolardi (1000 baravar kichik). Autogenerate buni O'ZI yozmaydi.

seller_rating (users) — pul EMAS, Numeric(3,2) bo'lib qoladi.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607170009"
down_revision: str | None = "202606210008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (jadval, ustun, nullable)
MONEY_COLUMNS: list[tuple[str, str, bool]] = [
    ("items", "starting_price", False),
    ("items", "reserve_price", True),
    ("auctions", "starting_price", False),
    ("auctions", "current_price", False),
    ("auctions", "minimum_bid_increment", False),
    ("auctions", "reserve_price", True),
    ("bids", "amount", False),
    ("orders", "final_price", False),
    ("payments", "amount", False),
]


def upgrade() -> None:
    for table, column, nullable in MONEY_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.BigInteger(),
            existing_type=sa.Numeric(12, 2),
            existing_nullable=nullable,
            # So'mni tiyinga o'girish. ROUND — Numeric'da kasr qismi
            # bo'lsa ham butun tiyin chiqsin (0.005 kabi qoldiq yo'qolmasin).
            postgresql_using=f"ROUND({column} * 100)::bigint",
        )

    # Har bid/narx musbat bo'lishi kerak. Ilgari bu faqat Pydantic'da
    # tekshirilardi — DB darajasida himoya yo'q edi.
    op.create_check_constraint("ck_items_starting_price_positive", "items", "starting_price > 0")
    op.create_check_constraint(
        "ck_auctions_starting_price_positive", "auctions", "starting_price > 0"
    )
    op.create_check_constraint(
        "ck_auctions_current_price_positive", "auctions", "current_price > 0"
    )
    op.create_check_constraint(
        "ck_auctions_min_increment_positive", "auctions", "minimum_bid_increment > 0"
    )
    op.create_check_constraint("ck_bids_amount_positive", "bids", "amount > 0")
    op.create_check_constraint("ck_orders_final_price_positive", "orders", "final_price > 0")
    op.create_check_constraint("ck_payments_amount_positive", "payments", "amount > 0")


def downgrade() -> None:
    op.drop_constraint("ck_payments_amount_positive", "payments", type_="check")
    op.drop_constraint("ck_orders_final_price_positive", "orders", type_="check")
    op.drop_constraint("ck_bids_amount_positive", "bids", type_="check")
    op.drop_constraint("ck_auctions_min_increment_positive", "auctions", type_="check")
    op.drop_constraint("ck_auctions_current_price_positive", "auctions", type_="check")
    op.drop_constraint("ck_auctions_starting_price_positive", "auctions", type_="check")
    op.drop_constraint("ck_items_starting_price_positive", "items", type_="check")

    for table, column, nullable in MONEY_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.Numeric(12, 2),
            existing_type=sa.BigInteger(),
            existing_nullable=nullable,
            postgresql_using=f"({column} / 100.0)::numeric(12,2)",
        )
