from datetime import UTC, datetime

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import OrderStatus
from app.money import Tiyin


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), unique=True, nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True, nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    # Pul — tiyinda (BIGINT). Batafsil: app/money/
    final_price: Mapped[Tiyin] = mapped_column(BigInteger, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SqlEnum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING_PAYMENT,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    auction = relationship("Auction", back_populates="order")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="orders_as_buyer")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="orders_as_seller")
    item = relationship("Item")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
