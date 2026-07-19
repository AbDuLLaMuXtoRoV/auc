"""webhook_events jadvali + payments held_at/released_at timestamptz

Revision ID: 202607170016
Revises: 202607170015
Create Date: 2026-07-17 00:16:00.000000

- webhook_events: PSP webhook dedup (provider+event_id unique).
- payments.held_at/released_at: naive timestamp -> timestamptz. Mavjud
  qiymatlar UTC deb talqin qilinadi (USING ... AT TIME ZONE 'UTC').
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607170016"
down_revision: str | None = "202607170015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "payments",
        "held_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="held_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "payments",
        "released_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="released_at AT TIME ZONE 'UTC'",
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),
    )
    op.create_index("ix_webhook_events_id", "webhook_events", ["id"])


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.alter_column("payments", "released_at", type_=sa.DateTime(timezone=False))
    op.alter_column("payments", "held_at", type_=sa.DateTime(timezone=False))
