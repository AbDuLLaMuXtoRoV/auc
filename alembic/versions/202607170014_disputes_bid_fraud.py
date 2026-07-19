"""disputes jadvali + bids anti-fraud ustunlari

Revision ID: 202607170014
Revises: 202607170013
Create Date: 2026-07-17 00:14:00.000000

- disputes: nizo oqimi (xaridor ochadi, admin hal qiladi).
- bids.ip / bids.device_id: shill halqasi / ko'p akkaunt aniqlash uchun.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607170014"
down_revision: str | None = "202607170013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dispute_reason = postgresql.ENUM(
        "NOT_RECEIVED",
        "NOT_AS_DESCRIBED",
        "DAMAGED",
        "FAKE",
        "OTHER",
        name="dispute_reason",
        create_type=False,
    )
    dispute_status = postgresql.ENUM(
        "OPEN",
        "UNDER_REVIEW",
        "RESOLVED_BUYER",
        "RESOLVED_SELLER",
        name="dispute_status",
        create_type=False,
    )
    bind = op.get_bind()
    dispute_reason.create(bind, checkfirst=True)
    dispute_status.create(bind, checkfirst=True)

    op.create_table(
        "disputes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("opened_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", dispute_reason, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", dispute_status, nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_disputes_id", "disputes", ["id"])
    op.create_index("ix_disputes_order_id", "disputes", ["order_id"])
    op.create_index("ix_disputes_opened_by", "disputes", ["opened_by"])
    op.create_index("ix_disputes_status", "disputes", ["status"])

    op.add_column("bids", sa.Column("ip", postgresql.INET(), nullable=True))
    op.add_column("bids", sa.Column("device_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("bids", "device_id")
    op.drop_column("bids", "ip")
    op.drop_table("disputes")
    bind = op.get_bind()
    sa.Enum(name="dispute_status").drop(bind, checkfirst=True)
    sa.Enum(name="dispute_reason").drop(bind, checkfirst=True)
