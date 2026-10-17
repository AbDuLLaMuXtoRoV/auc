"""Umumiy Redis mijozi — rate limit va kesh uchun.

`token_store.py` naqshi bilan bir xil: Redis IXTIYORIY. Paket yo'q, `redis_url`
bo'sh, yoki serverga ulanib bo'lmasa — `get_redis()` `None` qaytaradi va
chaqiruvchi xavfsiz zaxira yo'lga (in-memory / no-op) tushadi. Ilova hech qachon
Redis yo'qligi sababli yiqilmaydi.

Test muhitida har doim `None` — testlar ishlaydigan Redis talab qilmasin.
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis as _redis
except ImportError:  # pragma: no cover
    _redis = None

_client: _redis.Redis | None = None
_initialised = False


def get_redis() -> _redis.Redis | None:
    """Jarayon bo'yicha yagona Redis mijozi (yoki mavjud bo'lmasa None).

    Birinchi chaqiruvda ulanishni bir marta tekshiradi; muvaffaqiyatsiz bo'lsa
    `None` keshlab qo'yadi — har chaqiruvda qayta urinib sekinlashtirmaydi.
    """
    global _client, _initialised
    if _initialised:
        return _client

    _initialised = True
    if _redis is None or not settings.redis_url or settings.environment == "test":
        _client = None
        return None

    try:
        client = _redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _client = client
    except Exception:
        logger.warning("Redis'ga ulanib bo'lmadi — in-memory zaxiraga tushamiz")
        _client = None
    return _client


def reset_redis() -> None:
    """Keshlangan mijozni tozalaydi (testlar orasidagi izolyatsiya uchun)."""
    global _client, _initialised
    _client = None
    _initialised = False
