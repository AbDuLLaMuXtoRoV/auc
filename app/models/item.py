from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ItemCondition, ItemStatus
from app.money import Tiyin


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    condition: Mapped[ItemCondition] = mapped_column(
        SqlEnum(ItemCondition, name="item_condition"),
        default=ItemCondition.USED,
        nullable=False,
    )
    status: Mapped[ItemStatus] = mapped_column(
        SqlEnum(ItemStatus, name="item_status"),
        default=ItemStatus.DRAFT,
        nullable=False,
    )
    images: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    item_location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    # Pul — tiyinda (BIGINT). Batafsil: app/money/
    starting_price: Mapped[Tiyin] = mapped_column(BigInteger, nullable=False)
    reserve_price: Mapped[Tiyin | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    seller = relationship("User", back_populates="items")
    category = relationship("Category", back_populates="items")
    auction = relationship("Auction", back_populates="item", uselist=False)
    item_images = relationship(
        "ItemImage",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ItemImage.created_at",
    )


class ItemImage(Base):
    __tablename__ = "item_images"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    item = relationship("Item", back_populates="item_images")
