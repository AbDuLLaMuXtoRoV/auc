from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Review(Base):
    """Ikki tomonlama sharh — faqat COMPLETED order uchun.

    Xaridor va sotuvchi bir-birini baholaydi (1-5 yulduz). `to_id`ning
    `seller_rating` (o'rtacha) va `seller_rating_count` shundan hisoblanadi.
    Bir order uchun bir tomon bitta sharh qoldiradi (UNIQUE order_id+from_id).
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("order_id", "from_id", name="uq_reviews_order_from"),
        CheckConstraint("stars BETWEEN 1 AND 5", name="ck_reviews_stars_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    from_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    to_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    stars: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1..5
    text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    order = relationship("Order")
    author = relationship("User", foreign_keys=[from_id])
    target = relationship("User", foreign_keys=[to_id])
