"""handover va notification jadvallari

Revision ID: 202607170013
Revises: 202607170012
Create Date: 2026-07-17 00:13:00.000000

Post-Faza: topshirish (handover) va bildirishnoma (notification).
Enum turlari create_type=False bilan (CLAUDE.md qoidasi: aks holda
create_table CREATE TYPE ni ikkinchi marta yuborib yiqiladi).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607170013"
down_revision: str | None = "202607170012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    handover_method = postgresql.ENUM(
        "LOCAL_MEETUP", "DELIVERY", name="handover_method", create_type=False
    )
    handover_status = postgresql.ENUM(
        "PENDING", "COMPLETED", "FAILED", name="handover_status", create_type=False
    )
    notification_type = postgresql.ENUM(
        "OUTBID",
        "WON",
        "SOLD",
        "PAYMENT",
        "HANDOVER",
        "DISPUTE",
        name="notification_type",
        create_type=False,
    )
    bind = op.get_bind()
    handover_method.create(bind, checkfirst=True)
    handover_status.create(bind, checkfirst=True)
    notification_type.create(bind, checkfirst=True)

    op.create_table(
        "handovers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("method", handover_method, nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("status", handover_status, nullable=False),
        sa.Column("meet_address", sa.String(length=255), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_handovers_id", "handovers", ["id"])
    # order_id — unique index (model: unique=True, index=True) — 1 order = 1 handover.
    op.create_index("ix_handovers_order_id", "handovers", ["order_id"], unique=True)
    op.create_index("ix_handovers_status", "handovers", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("handovers")
    bind = op.get_bind()
    sa.Enum(name="notification_type").drop(bind, checkfirst=True)
    sa.Enum(name="handover_status").drop(bind, checkfirst=True)
    sa.Enum(name="handover_method").drop(bind, checkfirst=True)
