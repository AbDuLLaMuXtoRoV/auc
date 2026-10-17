from datetime import UTC, datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Watchlist(Base):
    """Foydalanuvchining kuzatuv ro'yxati: auksionni "yodda saqlash".

    Bir foydalanuvchi bitta auksionni faqat bir marta kuzata oladi
    (UniqueConstraint) — takror POST idempotent bo'ladi. Auksion o'chsa
    kuzatuv ham o'chadi (FK cascade migratsiyada emas, xizmat darajasida
    boshqariladi — hozir oddiy FK).
    """

    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "auction_id", name="uq_watchlist_user_auction"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    auction = relationship("Auction")
