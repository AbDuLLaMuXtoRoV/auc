from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import HandoverMethod, HandoverStatus


class Handover(Base):
    """Tovar topshirish yozuvi.

    Oqim: order PICKUP_PENDING (hold qilingan) -> sotuvchi handover yaratadi
    va `code` oladi -> uchrashuvda xaridorga kod aytiladi -> xaridor kodni
    kiritib tasdiqlaydi -> capture (pul sotuvchiga), order COMPLETED.

    Kod = egalik dalili: faqat tovarni qo'lida ushlagan xaridor uni biladi.
    """

    __tablename__ = "handovers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), unique=True, index=True, nullable=False
    )
    method: Mapped[HandoverMethod] = mapped_column(
        SqlEnum(HandoverMethod, name="handover_method"),
        default=HandoverMethod.LOCAL_MEETUP,
        nullable=False,
    )
    # Tasdiqlash kodi. Yashirin — API javobida faqat sotuvchiga ko'rsatiladi.
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[HandoverStatus] = mapped_column(
        SqlEnum(HandoverStatus, name="handover_status"),
        default=HandoverStatus.PENDING,
        index=True,
        nullable=False,
    )
    meet_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    order = relationship("Order")
