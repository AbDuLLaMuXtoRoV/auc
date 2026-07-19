from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PaymentStatus
from app.money import Tiyin


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="payment_methods")


class Payment(Base):
    __tablename__ = "payments"

    # Idempotentlik qalqoni: kalit unique (NULL'lar mustasno — partial index).
    __table_args__ = (
        Index(
            "uq_payments_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    # Pul — tiyinda (BIGINT). Batafsil: app/money/
    # amount — yakuniy narx (auksion current_price). premium — buyer premium 8%.
    # total — xaridor to'laydigan umumiy summa (amount + premium) = hold summasi.
    amount: Mapped[Tiyin] = mapped_column(BigInteger, nullable=False)
    premium: Mapped[Tiyin] = mapped_column(BigInteger, default=0, nullable=False)
    total: Mapped[Tiyin] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UZS", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SqlEnum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Idempotentlik: har pul operatsiyasi yagona kalit bilan. Unique index
    # ikki marta hold/capture'ning oldini oladi (parallel retry ham).
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # timezone-aware (timestamptz) — datetime.now(UTC) tz'sini saqlaydi.
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    order = relationship("Order", back_populates="payments")
    buyer = relationship("User")
