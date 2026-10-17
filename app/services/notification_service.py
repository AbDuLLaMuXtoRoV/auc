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
        created = self.notifications.create(notification)

        # Push yetkazishni fon vazifasiga topshiramiz (best-effort, so'rovni
        # bloklamaydi). Broker/worker yo'q bo'lsa enqueue() inline zaxiraga tushadi.
        # Lazy import — aylanma bog'liqlik va Celery'ni majburiy qilmaslik uchun.
        from app.tasks.dispatch import enqueue
        from app.tasks.notifications import deliver_push, deliver_telegram

        enqueue(
            deliver_push,
            user_id=user_id,
            title=title,
            body=body,
            data={"type": type.value, **(payload or {})},
        )

        # Telegram — O'zbekistonda asosiy kanal. Foydalanuvchi bot bilan
        # bog'langan (telegram_chat_id bor) bo'lsa, o'sha yerga ham yetkazamiz.
        # Best-effort: yetkazilmasa ham asosiy oqim (bid/to'lov) davom etadi.
        chat_id = self._telegram_chat_id(user_id)
        if chat_id:
            enqueue(
                deliver_telegram,
                chat_id=chat_id,
                text=self._telegram_text(title, body),
            )
        return created

    def _telegram_chat_id(self, user_id: int) -> str | None:
        """Foydalanuvchining Telegram chat_id'sini oladi (bog'lanmagan bo'lsa None)."""
        user = self.db.get(User, user_id)
        return user.telegram_chat_id if user else None

    @staticmethod
    def _telegram_text(title: str, body: str | None) -> str:
        """Telegram xabar matnini shakllantiradi: sarlavha + (ixtiyoriy) tana."""
        return f"{title}\n\n{body}" if body else title

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
