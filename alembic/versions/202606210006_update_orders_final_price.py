"""update orders final price

Revision ID: 202606210006
Revises: 202606210005
Create Date: 2026-06-21 00:06:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202606210006"
down_revision: str | None = "202606210005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("orders", "amount", new_column_name="final_price")
    op.drop_index(op.f("ix_orders_payment_status"), table_name="orders")
    op.drop_column("orders", "payment_status")


def downgrade() -> None:
    op.alter_column("orders", "final_price", new_column_name="amount")
    op.execute("ALTER TABLE orders ADD COLUMN payment_status payment_status")
    op.execute("UPDATE orders SET payment_status = 'PENDING' WHERE payment_status IS NULL")
    op.alter_column("orders", "payment_status", nullable=False)
    op.create_index(op.f("ix_orders_payment_status"), "orders", ["payment_status"], unique=False)
