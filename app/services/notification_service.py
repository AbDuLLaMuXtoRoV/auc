from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    """In-app bildirishnoma biznes mantiqi.

    `create` COMMIT QILMAYDI — u event hook'lardan (bid, close, payment) tranzaksiya
    ichida chaqiriladi va shu tranzaksiya bilan atomik bo'lishi kerak. Standalone
    endpoint'lar (mark_read, mark_all_read) esa o'zi commit qiladi.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)

    def create(
        self,
        *,
        user_id: int,
        type: NotificationType,
        title: str,
        body: str | None = None,
        payload: dict | None = None,
    ) -> Notification:
        # Faqat flush — chaqiruvchi tranzaksiya commit'ini boshqaradi.
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            payload=payload,
        )
        return self.notifications.create(notification)

    def list_mine(self, user: User, only_unread: bool = False) -> list[Notification]:
        return self.notifications.list_for_user(user.id, only_unread=only_unread)

    def mark_read(self, notification_id: int, user: User) -> Notification:
        notification = self._get_owned(notification_id, user)
        self.notifications.mark_read(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_read(self, user: User) -> int:
        count = self.notifications.mark_all_read(user.id)
        self.db.commit()
        return count

    def unread_count(self, user: User) -> int:
        return self.notifications.unread_count(user.id)

    def _get_owned(self, notification_id: int, user: User) -> Notification:
        """Bildirishnomani egalik tekshiruvi bilan oladi.

        Mavjud emas yoki boshqa foydalanuvchiniki — ikkalasi ham 404: begonaga
        boshqaning notif'i mavjudligini oshkor qilmaymiz (IDOR himoyasi).
        """
        notification = self.notifications.get(notification_id)
        if notification is None or notification.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )
        return notification
