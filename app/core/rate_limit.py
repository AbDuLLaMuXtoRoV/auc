"""Oddiy process-ichi (in-memory) rate limiter.

Login va bid endpointlarini brute-force / spam'dan himoya qiladi. Har mijoz
(IP bo'yicha) belgilangan oyna (window) ichida cheklangan sondagi so'rov qila
oladi; oshsa `429 Too Many Requests` qaytadi.

Nega settings chaqiruv paytida o'qiladi (import paytida emas): shunda testlar
`monkeypatch.setattr(settings, ...)` bilan muhit va limitlarni o'zgartira oladi.

TODO(kelajak): bu limiter faqat bitta process ichida to'g'ri ishlaydi. Bir
nechta uvicorn worker (yoki bir nechta instans) ishlaganda har biri o'z
hisobini alohida yuritadi — real limit worker soniga ko'payadi. Ishlab
chiqarishda umumiy holat uchun Redis (sliding-window yoki token-bucket) kerak.
"""

from __future__ import annotations

import threading
import time

from fastapi import HTTPException, Request, status

from app.core.config import settings

# (identifier, scope) -> shu oynadagi so'rov vaqtlari (monotonic sekundlar).
_hits: dict[tuple[str, str], list[float]] = {}
_lock = threading.Lock()

# scope -> qaysi settings maydonidan limit o'qilishi. Limit qiymati chaqiruv
# paytida shu jadval orqali olinadi, import paytida qotib qolmaydi.
_SCOPE_LIMIT_SETTING: dict[str, str] = {
    "login": "rate_limit_login_per_minute",
    "bid": "rate_limit_bid_per_minute",
}


def reset_rate_limits() -> None:
    """Barcha hisoblangan holatni tozalaydi (testlar orasida ishlatiladi)."""
    with _lock:
        _hits.clear()


def _client_identifier(request: Request) -> str:
    """Mijozni IP bo'yicha aniqlaydi; aniqlab bo'lmasa 'unknown'."""
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


class RateLimiter:
    """FastAPI dependency: bitta scope uchun mijoz IP'iga oyna bo'yicha limit.

    scope orqali qaysi settings maydonidan limit olishni biladi (masalan
    scope="login" -> `settings.rate_limit_login_per_minute`). Limit qiymati
    dependency chaqirilganda o'qiladi, shuning uchun test monkeypatch qila oladi.
    """

    def __init__(self, scope: str, window_seconds: int = 60) -> None:
        if scope not in _SCOPE_LIMIT_SETTING:
            raise ValueError(f"Noma'lum rate-limit scope: {scope!r}")
        self.scope = scope
        self.window_seconds = window_seconds

    def _limit(self) -> int:
        """Joriy limitni settings'dan (chaqiruv paytida) o'qiydi."""
        return getattr(settings, _SCOPE_LIMIT_SETTING[self.scope])

    def __call__(self, request: Request) -> None:
        # Limiter faqat yoqilgan va NON-test muhitda ishlaydi. Aks holda no-op:
        # test to'plami ko'p marta login/bid qiladi, ular 429 olmasligi kerak.
        if not settings.rate_limit_enabled or settings.environment == "test":
            return

        limit = self._limit()
        key = (_client_identifier(request), self.scope)
        now = time.monotonic()
        window_start = now - self.window_seconds

        with _lock:
            hits = _hits.setdefault(key, [])
            # Oynadan chiqib ketgan eski urinishlarni tashlab yuboramiz.
            hits[:] = [ts for ts in hits if ts > window_start]
            if len(hits) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Juda ko'p so'rov. Birozdan keyin qayta urinib ko'ring.",
                )
            hits.append(now)
