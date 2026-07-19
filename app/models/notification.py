from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import NotificationType


class Notification(Base):
    """Foydalanuvchiga in-app bildirishnoma.

    Eventlar: OUTBID (ortda qolish), WON, SOLD, PAYMENT, HANDOVER, DISPUTE.
    Push (FCM/APNs) keyin qo'shiladi — hozir in-app (DB) yetarli.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    type: Mapped[NotificationType] = mapped_column(
        SqlEnum(NotificationType, name="notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Qo'shimcha ma'lumot (auction_id, amount, ...) — mijoz uchun.
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(default=False, index=True, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User")
