"""update messages read state

Revision ID: 202606210008
Revises: 202606210007
Create Date: 2026-06-21 00:08:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606210008"
down_revision: str | None = "202606210007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("is_read", sa.Boolean(), nullable=True))
    op.execute("UPDATE messages SET is_read = FALSE WHERE is_read IS NULL")
    op.alter_column("messages", "is_read", nullable=False)
    op.drop_column("messages", "read_at")


def downgrade() -> None:
    op.add_column("messages", sa.Column("read_at", sa.DateTime(), nullable=True))
    op.drop_column("messages", "is_read")
