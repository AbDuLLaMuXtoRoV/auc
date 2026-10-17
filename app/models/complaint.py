from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ComplaintStatus, ComplaintTargetType


class Complaint(Base):
    """Shikoyat: foydalanuvchi tovar/foydalanuvchi/auksion va h.k. ustidan
    xabar beradi, admin ko'rib chiqadi.

    `target_type` + `target_id` — polimorfik havola: qaysi obyekt haqida
    shikoyat ekani. Alohida FK qo'yilmaydi (turi o'zgaruvchan), integritet
    xizmat darajasida. Status OPEN -> REVIEWING -> RESOLVED/REJECTED oqimi
    bo'yicha admin tomonidan yuritiladi.
    """

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    target_type: Mapped[ComplaintTargetType] = mapped_column(
        SqlEnum(ComplaintTargetType, name="complaint_target_type"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ComplaintStatus] = mapped_column(
        SqlEnum(ComplaintStatus, name="complaint_status"),
        default=ComplaintStatus.OPEN,
        index=True,
        nullable=False,
    )
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_id])
    resolver = relationship("User", foreign_keys=[resolved_by_id])
