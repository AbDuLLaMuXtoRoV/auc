"""escrow: payment holatlari, premium/total, idempotency, audit_log, auto_complete

Revision ID: 202607170012
Revises: 202607170011
Create Date: 2026-07-17 00:12:00.000000

Faza D poydevori:
- payment_status enum'iga held/released/cancelled_hold qo'shiladi.
- payments: premium, total, idempotency_key (unique), held_at, released_at,
  failed_reason.
- orders.auto_complete_at.
- audit_log jadvali (INSERT only — pul harakatlari dalili).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607170012"
down_revision: str | None = "202607170011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum qiymatlari (ADD VALUE — mavjud migratsiya naqshi).
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'held'")
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'released'")
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'cancelled_hold'")

    # payments ustunlari
    op.add_column(
        "payments", sa.Column("premium", sa.BigInteger(), nullable=False, server_default="0")
    )
    op.add_column(
        "payments", sa.Column("total", sa.BigInteger(), nullable=False, server_default="0")
    )
    op.add_column("payments", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("payments", sa.Column("held_at", sa.DateTime(), nullable=True))
    op.add_column("payments", sa.Column("released_at", sa.DateTime(), nullable=True))
    op.add_column("payments", sa.Column("failed_reason", sa.String(length=255), nullable=True))
    op.alter_column("payments", "premium", server_default=None)
    op.alter_column("payments", "total", server_default=None)
    # Idempotentlik qalqoni: kalit unique (NULL'lar bundan mustasno).
    op.create_index(
        "uq_payments_idempotency_key",
        "payments",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    # orders.auto_complete_at
    op.add_column(
        "orders", sa.Column("auto_complete_at", sa.DateTime(timezone=True), nullable=True)
    )

    # audit_log (INSERT only)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_entity_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_column("orders", "auto_complete_at")
    op.drop_index("uq_payments_idempotency_key", table_name="payments")
    op.drop_column("payments", "failed_reason")
    op.drop_column("payments", "released_at")
    op.drop_column("payments", "held_at")
    op.drop_column("payments", "idempotency_key")
    op.drop_column("payments", "total")
    op.drop_column("payments", "premium")
    # Postgres enum'dan qiymat olib tashlash murakkab (yangi tur yaratish kerak);
    # downgrade'da qoldiriladi — zararsiz (ishlatilmagan qiymat).
