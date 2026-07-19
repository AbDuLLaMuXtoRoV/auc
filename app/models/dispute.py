from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import DisputeReason, DisputeStatus


class Dispute(Base):
    """Nizo: xaridor tovar bilan muammo bo'lganda ochadi.

    Oqim: payment HELD holatida xaridor nizo ochadi -> auto-complete
    TO'XTAYDI (pul muzlab qoladi) -> admin dalillarni ko'radi -> qaror:
      RESOLVED_SELLER -> capture (pul sotuvchiga)
      RESOLVED_BUYER  -> release (blok bekor, pul xaridorda)
    """

    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    opened_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    reason: Mapped[DisputeReason] = mapped_column(
        SqlEnum(DisputeReason, name="dispute_reason"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DisputeStatus] = mapped_column(
        SqlEnum(DisputeStatus, name="dispute_status"),
        default=DisputeStatus.OPEN,
        index=True,
        nullable=False,
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    order = relationship("Order")
    opener = relationship("User", foreign_keys=[opened_by])
