"""enqueue() — vazifani navbatga qo'yish, broker yo'q bo'lsa inline zaxira.

So'rov oqimidan (masalan notification_service) chaqiriladi. Celery eager
rejimida yoki broker'ga ulanib bo'lmasa, vazifa `task.apply()` orqali shu yerda
(sinxron) bajariladi — istisnolar natijaga yig'iladi, chaqiruvchini yiqitmaydi.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import Task

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


def enqueue(task: Task, *args: Any, **kwargs: Any) -> Any:
    """Vazifani navbatga qo'yadi; broker yo'q bo'lsa inline bajaradi.

    Hech qachon istisno ko'tarmaydi va HECH QACHON bloklanmaydi — broker (Redis)
    yetib bo'lmasa `task.delay` ulanishni kutib qotib qolishi mumkin, shuning
    uchun avval `get_redis()` (tez, keshlangan ping) bilan tekshiramiz. Redis
    yo'q yoki eager rejim -> vazifa shu yerda (inline, istisnolar yig'iladi)
    bajariladi. Push/email yetkazilmasa ham asosiy biznes-oqim davom etaveradi.
    """
    if settings.celery_eager or get_redis() is None:
        return task.apply(args=list(args), kwargs=kwargs)
    try:
        return task.delay(*args, **kwargs)
    except Exception:
        logger.warning("Broker'ga ulanib bo'lmadi — %s inline bajarilmoqda", task.name)
        return task.apply(args=list(args), kwargs=kwargs)
