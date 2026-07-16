from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    seller_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    seller_rating_count: Mapped[int] = mapped_column(default=0, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"),
        default=UserRole.USER,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    items = relationship("Item", back_populates="seller", cascade="all, delete-orphan")
    auctions = relationship(
        "Auction",
        foreign_keys="Auction.seller_id",
        back_populates="seller",
    )
    bids = relationship("Bid", back_populates="bidder")
    won_auctions = relationship(
        "Auction",
        foreign_keys="Auction.winner_id",
        back_populates="winner",
    )
    payment_methods = relationship(
        "PaymentMethod",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    orders_as_buyer = relationship(
        "Order",
        foreign_keys="Order.buyer_id",
        back_populates="buyer",
    )
    orders_as_seller = relationship(
        "Order",
        foreign_keys="Order.seller_id",
        back_populates="seller",
    )
