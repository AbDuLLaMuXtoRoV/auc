"""add marketplace auctions

Revision ID: 202606210002
Revises: 202606210001
Create Date: 2026-06-21 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202606210002"
down_revision: str | None = "202606210001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # create_type=False MAJBURIY: turlar quyida aniq (checkfirst bilan)
    # yaratiladi. Oddiy sa.Enum ishlatilsa, create_table ustunni ko'rib
    # CREATE TYPE ni IKKINCHI marta yuboradi — endi checkfirst'siz — va
    # "type already exists" xatosi bilan yiqiladi. Ya'ni toza bazada
    # `alembic upgrade head` umuman ishlamaydi.
    item_condition = postgresql.ENUM(
        "NEW", "LIKE_NEW", "GOOD", "FAIR", "FOR_PARTS", name="item_condition", create_type=False
    )
    item_status = postgresql.ENUM(
        "DRAFT", "LISTED", "ARCHIVED", name="item_status", create_type=False
    )
    auction_status = postgresql.ENUM(
        "DRAFT", "ACTIVE", "ENDED", "CANCELLED", name="auction_status", create_type=False
    )
    bid_status = postgresql.ENUM(
        "VALID", "OUTBID", "CANCELLED", name="bid_status", create_type=False
    )

    item_condition.create(op.get_bind(), checkfirst=True)
    item_status.create(op.get_bind(), checkfirst=True)
    auction_status.create(op.get_bind(), checkfirst=True)
    bid_status.create(op.get_bind(), checkfirst=True)

    op.add_column("users", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("location", sa.String(length=160), nullable=True))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE users SET updated_at = created_at")
    op.alter_column("users", "updated_at", nullable=False)

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("condition", item_condition, nullable=False),
        sa.Column("status", item_status, nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("starting_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_category"), "items", ["category"], unique=False)
    op.create_index(op.f("ix_items_id"), "items", ["id"], unique=False)
    op.create_index(op.f("ix_items_seller_id"), "items", ["seller_id"], unique=False)
    op.create_index(op.f("ix_items_title"), "items", ["title"], unique=False)

    op.create_table(
        "auctions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", auction_status, nullable=False),
        sa.Column("starting_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("winning_bid_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id"),
    )
    op.create_index(op.f("ix_auctions_ends_at"), "auctions", ["ends_at"], unique=False)
    op.create_index(op.f("ix_auctions_id"), "auctions", ["id"], unique=False)
    op.create_index(op.f("ix_auctions_seller_id"), "auctions", ["seller_id"], unique=False)
    op.create_index(op.f("ix_auctions_status"), "auctions", ["status"], unique=False)

    op.create_table(
        "bids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auction_id", sa.Integer(), nullable=False),
        sa.Column("bidder_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", bid_status, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["auction_id"], ["auctions.id"]),
        sa.ForeignKeyConstraint(["bidder_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bids_auction_id"), "bids", ["auction_id"], unique=False)
    op.create_index(op.f("ix_bids_bidder_id"), "bids", ["bidder_id"], unique=False)
    op.create_index(op.f("ix_bids_id"), "bids", ["id"], unique=False)
    op.create_index(op.f("ix_bids_status"), "bids", ["status"], unique=False)
    op.create_foreign_key(
        "fk_auctions_winning_bid_id_bids",
        "auctions",
        "bids",
        ["winning_bid_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_auctions_winning_bid_id_bids", "auctions", type_="foreignkey")
    op.drop_index(op.f("ix_bids_status"), table_name="bids")
    op.drop_index(op.f("ix_bids_id"), table_name="bids")
    op.drop_index(op.f("ix_bids_bidder_id"), table_name="bids")
    op.drop_index(op.f("ix_bids_auction_id"), table_name="bids")
    op.drop_table("bids")

    op.drop_index(op.f("ix_auctions_status"), table_name="auctions")
    op.drop_index(op.f("ix_auctions_seller_id"), table_name="auctions")
    op.drop_index(op.f("ix_auctions_id"), table_name="auctions")
    op.drop_index(op.f("ix_auctions_ends_at"), table_name="auctions")
    op.drop_table("auctions")

    op.drop_index(op.f("ix_items_title"), table_name="items")
    op.drop_index(op.f("ix_items_seller_id"), table_name="items")
    op.drop_index(op.f("ix_items_id"), table_name="items")
    op.drop_index(op.f("ix_items_category"), table_name="items")
    op.drop_table("items")

    op.drop_column("users", "updated_at")
    op.drop_column("users", "location")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "bio")
    op.drop_column("users", "phone")

    bind = op.get_bind()
    sa.Enum(name="bid_status").drop(bind, checkfirst=True)
    sa.Enum(name="auction_status").drop(bind, checkfirst=True)
    sa.Enum(name="item_status").drop(bind, checkfirst=True)
    sa.Enum(name="item_condition").drop(bind, checkfirst=True)
