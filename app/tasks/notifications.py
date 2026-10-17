"""Push bildirishnoma yetkazish vazifasi (queue).

In-app yozuv DB'ga tushgach (`notification_service.create`), push yetkazish
so'rov oqimidan chiqarib, shu vazifaga topshiriladi — foydalanuvchi kutmaydi.
Yetkazish `push_provider` abstraksiyasi orqali (hozir LogPushProvider).
"""

from __future__ import annotations

import logging

from app.core.celery_app import celery_app
from app.services.push_provider import PushProviderError, get_push_provider
from app.services.telegram_provider import get_telegram_provider

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notifications.deliver_push")
def deliver_push(
    user_id: int,
    title: str,
    body: str | None = None,
    data: dict | None = None,
    provider: str = "log",
) -> str | None:
    """Foydalanuvchiga push yuboradi. message_id qaytaradi (yoki None)."""
    try:
        result = get_push_provider(provider).send(
            user_id=user_id, title=title, body=body, data=data
        )
        return result.message_id
    except PushProviderError:
        # Noma'lum provayder — konfiguratsiya xatosi, qayta urinish foydasiz.
        logger.exception("Push provayderi noto'g'ri: %s", provider)
        return None


@celery_app.task(name="app.tasks.notifications.deliver_telegram")
def deliver_telegram(chat_id: str, text: str) -> bool:
    """Foydalanuvchining Telegram chat'iga xabar yetkazadi (best-effort).

    Provayder tanlovi `get_telegram_provider()` da (token bo'lsa Http, aks holda
    Log). Yetkazish xatolari provayder ichida yutiladi — bu vazifa hech qachon
    biznes-oqimni to'xtatmaydi, faqat yetkazildi/yo'q (bool) qaytaradi.
    """
    return get_telegram_provider().send_message(chat_id, text)
