from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, text
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
        # Idempotentlik: bir bidder bir idempotency_key bilan FAQAT bitta bid
        # yozadi (tarmoq qayta urinishi ikkilamchi bid yaratmasin). PARTIAL —
        # faqat kalit berilganda amal qiladi; kalitsiz bidlar cheklanmaydi.
        Index(
            "uq_bids_bidder_idempotency_key",
            "bidder_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
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
    # Audit izi: qaysi brauzer/ilova bid qo'ygan (anti-fraud, nizo tekshiruvi).
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Idempotentlik kaliti — mijoz beradi. Bir xil kalit bilan takroriy so'rov
    # yangi bid yaratmaydi (partial unique index bilan qo'llab-quvvatlanadi).
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[BidStatus] = mapped_column(
        SqlEnum(BidStatus, name="bid_status"),
        default=BidStatus.VALID,
        index=True,
        nullable=False,
    )
    # Retraction/invalidation audit izi: kim bekor qildi va nima sababdan.
    # retracted_by_id — o'z bidini qaytargan foydalanuvchi YOKI invalidatsiya
    # qilgan admin. retract_reason — admin invalidatsiyasida majburiy sabab.
    #
    # DIQQAT: bu ustun users.id ga MODEL-DARAJADA ForeignKey EMAS. Sabab: bids
    # jadvalida users.id ga ikkinchi FK paydo bo'lsa, TAQIQLANGAN user.py dagi
    # `User.bids = relationship(...)` (foreign_keys ko'rsatilmagan) noaniq bo'lib
    # butun mapper konfiguratsiyasi yiqiladi. FK constraint'ni DB-darajada
    # migratsiyada qo'shsa bo'ladi — u ORM join'iga ta'sir qilmaydi (notes).
    retracted_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    retract_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    auction = relationship("Auction", back_populates="bids", foreign_keys=[auction_id])
    bidder = relationship("User", back_populates="bids")
