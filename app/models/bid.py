from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import BidStatus
from app.money import Tiyin


class Bid(Base):
    __tablename__ = "bids"

    # G'olib bidni topish uchun kompozit index: auksion bo'yicha eng yuqori
    # amount, teng bo'lsa eng erta created_at (get_highest_valid_bid).
    __table_args__ = (
        Index("ix_bids_auction_amount_created", "auction_id", "amount", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), index=True, nullable=False)
    bidder_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    # Pul — tiyinda (BIGINT). Batafsil: app/money/
    # amount — bid qo'yilganda ko'ringan narx (visible).
    amount: Mapped[Tiyin] = mapped_column(BigInteger, nullable=False)
    # max_amount — proxy shift: foydalanuvchi to'lashga tayyor MAKSIMAL summa.
    # HECH QACHON API javobida oshkor bo'lmaydi (BidRead'da yo'q).
    # max_amount berilmasa = amount (proxy o'chiq, oddiy bid).
    max_amount: Mapped[Tiyin] = mapped_column(BigInteger, nullable=False)
    # is_proxy — bu yozuv tizim tomonidan avtomatik ko'tarilganmi (leader himoyasi).
    is_proxy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Anti-fraud izlari: shill halqasi / bir qurilmadan ko'p akkaunt aniqlash.
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[BidStatus] = mapped_column(
        SqlEnum(BidStatus, name="bid_status"),
        default=BidStatus.VALID,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    auction = relationship("Auction", back_populates="bids", foreign_keys=[auction_id])
    bidder = relationship("User", back_populates="bids")
