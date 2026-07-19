from fastapi import APIRouter

from app.core.dependencies import CurrentActiveUser, DbSession
from app.models.notification import Notification
from app.schemas.notification import NotificationRead, UnreadCount
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=list[NotificationRead])
def read_my_notifications(
    current_user: CurrentActiveUser,
    db: DbSession,
    only_unread: bool = False,
) -> list[Notification]:
    return NotificationService(db).list_mine(current_user, only_unread=only_unread)


@router.get("/unread-count", response_model=UnreadCount)
def read_unread_count(current_user: CurrentActiveUser, db: DbSession) -> UnreadCount:
    return UnreadCount(count=NotificationService(db).unread_count(current_user))


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> Notification:
    return NotificationService(db).mark_read(notification_id, current_user)


@router.post("/read-all", response_model=UnreadCount)
def mark_all_notifications_read(current_user: CurrentActiveUser, db: DbSession) -> UnreadCount:
    # Qaytgan `count` — o'qilgan (o'zgargan) bildirishnomalar soni.
    return UnreadCount(count=NotificationService(db).mark_all_read(current_user))
