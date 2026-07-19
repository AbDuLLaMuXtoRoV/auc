from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    """Bildirishnoma jadvaliga kirish — faqat DB o'qish/yozish."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, notification: Notification) -> Notification:
        # flush — commit EMAS. Chaqiruvchi (event hook yoki endpoint) tranzaksiyani
        # o'zi yopadi, shunda bildirishnoma bid/close bilan bir xil atomlikda qoladi.
        self.db.add(notification)
        self.db.flush()
        return notification

    def get(self, notification_id: int) -> Notification | None:
        return self.db.get(Notification, notification_id)

    def list_for_user(self, user_id: int, only_unread: bool = False) -> list[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if only_unread:
            statement = statement.where(Notification.is_read.is_(False))
        statement = statement.order_by(Notification.created_at.desc())
        return list(self.db.scalars(statement))

    def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        self.db.add(notification)
        return notification

    def mark_all_read(self, user_id: int) -> int:
        # Bittalab yuklamasdan to'g'ridan-to'g'ri UPDATE — o'qilmaganlar soni qaytadi.
        now = datetime.now(UTC)
        statement = (
            Notification.__table__.update()
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=now)
        )
        result = self.db.execute(statement)
        return result.rowcount or 0

    def unread_count(self, user_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return self.db.scalar(statement) or 0
