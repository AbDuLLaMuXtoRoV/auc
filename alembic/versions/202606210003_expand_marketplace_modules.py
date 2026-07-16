"""expand marketplace modules

Revision ID: 202606210003
Revises: 202606210002
Create Date: 2026-06-21 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202606210003"
down_revision: str | None = "202606210002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('USER', 'SELLER', 'ADMIN')")
    op.execute("ALTER TYPE item_condition ADD VALUE IF NOT EXISTS 'USED'")
    op.execute("ALTER TYPE item_condition ADD VALUE IF NOT EXISTS 'REFURBISHED'")
    op.execute("ALTER TYPE item_status ADD VALUE IF NOT EXISTS 'PENDING'")
    op.execute("ALTER TYPE item_status ADD VALUE IF NOT EXISTS 'ACTIVE'")
    op.execute("ALTER TYPE item_status ADD VALUE IF NOT EXISTS 'SOLD'")
    op.execute("ALTER TYPE item_status ADD VALUE IF NOT EXISTS 'CANCELLED'")
    op.execute("ALTER TYPE auction_status ADD VALUE IF NOT EXISTS 'SCHEDULED'")
    op.execute("ALTER TYPE auction_status ADD VALUE IF NOT EXISTS 'RESERVE_NOT_MET'")
    op.execute("CREATE TYPE payment_status AS ENUM ('PENDING', 'PAID', 'FAILED', 'REFUNDED')")
    op.execute(
        "CREATE TYPE order_status AS ENUM "
        "('PENDING_PAYMENT', 'PAID', 'PICKUP_PENDING', 'COMPLETED', 'CANCELLED')"
    )

    op.add_column("users", sa.Column("seller_rating", sa.Numeric(3, 2), nullable=True))
    op.add_column("users", sa.Column("seller_rating_count", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=True))
    op.add_column("users", sa.Column("role", sa.Enum(name="user_role"), nullable=True))
    op.execute("UPDATE users SET seller_rating = 0 WHERE seller_rating IS NULL")
    op.execute("UPDATE users SET seller_rating_count = 0 WHERE seller_rating_count IS NULL")
    op.execute("UPDATE users SET is_verified = FALSE WHERE is_verified IS NULL")
    op.execute("UPDATE users SET role = 'USER' WHERE role IS NULL")
    op.alter_column("users", "seller_rating", nullable=False)
    op.alter_column("users", "seller_rating_count", nullable=False)
    op.alter_column("users", "is_verified", nullable=False)
    op.alter_column("users", "role", nullable=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=True)

    op.add_column("items", sa.Column("category_id", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("images", sa.JSON(), nullable=True))
    op.add_column("items", sa.Column("item_location", sa.String(length=160), nullable=True))
    op.add_column("items", sa.Column("reserve_price", sa.Numeric(12, 2), nullable=True))
    op.execute("UPDATE items SET images = '[]'::json WHERE images IS NULL")
    op.alter_column("items", "images", nullable=False)
    op.create_foreign_key(
        "fk_items_category_id_categories", "items", "categories", ["category_id"], ["id"]
    )
    op.create_index(op.f("ix_items_category_id"), "items", ["category_id"], unique=False)
    op.drop_index(op.f("ix_items_category"), table_name="items")
    op.drop_column("items", "category")

    op.alter_column("auctions", "starts_at", new_column_name="start_time")
    op.alter_column("auctions", "ends_at", new_column_name="end_time")
    op.add_column("auctions", sa.Column("minimum_bid_increment", sa.Numeric(12, 2), nullable=True))
    op.add_column("auctions", sa.Column("reserve_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("auctions", sa.Column("winner_id", sa.Integer(), nullable=True))
    op.execute("UPDATE auctions SET minimum_bid_increment = 1 WHERE minimum_bid_increment IS NULL")
    op.alter_column("auctions", "minimum_bid_increment", nullable=False)
    op.create_foreign_key("fk_auctions_winner_id_users", "auctions", "users", ["winner_id"], ["id"])
    op.create_index(op.f("ix_auctions_winner_id"), "auctions", ["winner_id"], unique=False)
    op.drop_index(op.f("ix_auctions_ends_at"), table_name="auctions")
    op.create_index(op.f("ix_auctions_end_time"), "auctions", ["end_time"], unique=False)

    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("token_reference", sa.String(length=255), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_methods_id"), "payment_methods", ["id"], unique=False)
    op.create_index(
        op.f("ix_payment_methods_user_id"), "payment_methods", ["user_id"], unique=False
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auction_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.Enum(name="order_status"), nullable=False),
        sa.Column("payment_status", sa.Enum(name="payment_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["auction_id"], ["auctions.id"]),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auction_id"),
    )
    op.create_index(op.f("ix_orders_buyer_id"), "orders", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)
    op.create_index(op.f("ix_orders_item_id"), "orders", ["item_id"], unique=False)
    op.create_index(op.f("ix_orders_payment_status"), "orders", ["payment_status"], unique=False)
    op.create_index(op.f("ix_orders_seller_id"), "orders", ["seller_id"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_buyer_id"), "conversations", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_conversations_id"), "conversations", ["id"], unique=False)
    op.create_index(op.f("ix_conversations_item_id"), "conversations", ["item_id"], unique=False)
    op.create_index(
        op.f("ix_conversations_seller_id"), "conversations", ["seller_id"], unique=False
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False
    )
    op.create_index(op.f("ix_messages_id"), "messages", ["id"], unique=False)
    op.create_index(op.f("ix_messages_sender_id"), "messages", ["sender_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_sender_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_conversations_seller_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_item_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_buyer_id"), table_name="conversations")
    op.drop_table("conversations")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_seller_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_payment_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_item_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_buyer_id"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_payment_methods_user_id"), table_name="payment_methods")
    op.drop_index(op.f("ix_payment_methods_id"), table_name="payment_methods")
    op.drop_table("payment_methods")
    op.drop_index(op.f("ix_auctions_end_time"), table_name="auctions")
    op.create_index(op.f("ix_auctions_ends_at"), "auctions", ["end_time"], unique=False)
    op.drop_index(op.f("ix_auctions_winner_id"), table_name="auctions")
    op.drop_constraint("fk_auctions_winner_id_users", "auctions", type_="foreignkey")
    op.drop_column("auctions", "winner_id")
    op.drop_column("auctions", "reserve_price")
    op.drop_column("auctions", "minimum_bid_increment")
    op.alter_column("auctions", "end_time", new_column_name="ends_at")
    op.alter_column("auctions", "start_time", new_column_name="starts_at")
    op.drop_index(op.f("ix_items_category_id"), table_name="items")
    op.drop_constraint("fk_items_category_id_categories", "items", type_="foreignkey")
    op.add_column("items", sa.Column("category", sa.String(length=80), nullable=True))
    op.drop_column("items", "reserve_price")
    op.drop_column("items", "item_location")
    op.drop_column("items", "images")
    op.drop_column("items", "category_id")
    op.create_index(op.f("ix_items_category"), "items", ["category"], unique=False)
    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")
    op.drop_column("users", "is_verified")
    op.drop_column("users", "seller_rating_count")
    op.drop_column("users", "seller_rating")
    op.execute("DROP TYPE order_status")
    op.execute("DROP TYPE payment_status")
    op.execute("DROP TYPE user_role")
