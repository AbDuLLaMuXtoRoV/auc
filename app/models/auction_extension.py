from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AuctionExtension(Base):
    """Anti-sniping natijasida auksion muddatining uzaytirilishi (audit izi).

    Har uzaytirish alohida qator: qaysi bid sabab bo'ldi, eski/yangi tugash
    vaqti nima edi. Auksiondagi `extension_count` — jami son; bu jadval esa
    to'liq tarixni saqlaydi (kim, qachon, qancha cho'zdi — nizoda muhim).

    Bu faylni auksion dvigateli (soft-close) yozadi; hozir faqat model.
    """

    __tablename__ = "auction_extensions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), index=True, nullable=False)
    old_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    triggered_by_bid_id: Mapped[int | None] = mapped_column(ForeignKey("bids.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    auction = relationship("Auction")
