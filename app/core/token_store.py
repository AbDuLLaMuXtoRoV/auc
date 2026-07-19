"""Token bekor qilish (logout) do'koni — abstraksiya.

Nega kerak: JWT stateless, shuning uchun logout qilingan tokenni "bekor
qilingan" deb belgilash uchun server tarafida ro'yxat kerak (blacklist).
Ilgari bu ro'yxat `security.py` ichida oddiy `set` edi — process-ichi
in-memory. Bu ikki muammoni keltiradi:
  * restart'da ro'yxat yo'qoladi → bekor qilingan token yana ishlaydi;
  * ko'p-worker (gunicorn/uvicorn --workers) da har worker o'z set'iga ega →
    bir worker'da logout qilingan token boshqasida hali amal qiladi.
Har ikkalasi ham logoutni ishonchsiz qiladi (security review topilmasi).

Yechim: `TokenRevocationStore` abstraksiyasi. Default — `InMemoryTokenStore`
(testlar va bitta-worker local uchun, hozirgi xatti-harakat aynan). Prod'da
esa Redis-backed variant barcha worker'lar orasida umumiy holat beradi.

Redis IXTIYORIY bog'liqlik: `redis` paketi o'rnatilmagan yoki serverga
ulanib bo'lmasa, fabrika xavfsiz tarzda in-memory'ga tushadi — ilova
ko'tarilishdan to'xtamaydi.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings

# Redis GUARDED import: paket bo'lmasa ham modul import bo'laversin.
# Qattiq bog'liqlik qo'shmaymiz — redis faqat prod'da ulanadi.
try:
    import redis as _redis
except ImportError:  # pragma: no cover — redis o'rnatilmagan muhit
    _redis = None


class TokenRevocationStore(ABC):
    """Bekor qilingan token jti'larini saqlovchi do'kon interfeysi."""

    @abstractmethod
    def revoke(self, jti: str) -> None:
        """`jti` ni bekor qilingan deb belgilaydi."""
        raise NotImplementedError

    @abstractmethod
    def is_revoked(self, jti: str) -> bool:
        """`jti` bekor qilinganmi — True/False."""
        raise NotImplementedError


class InMemoryTokenStore(TokenRevocationStore):
    """Process-ichi `set` ustidagi do'kon.

    Default variant. Restart va ko'p-worker'da holat ulashilmaydi — shuning
    uchun faqat test/bitta-worker local uchun mos. Hozirgi (eski) xatti-harakat
    bilan aynan bir xil.
    """

    def __init__(self) -> None:
        self._revoked: set[str] = set()

    def revoke(self, jti: str) -> None:
        self._revoked.add(jti)

    def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked


class RedisTokenStore(TokenRevocationStore):
    """Redis-backed do'kon — barcha worker'lar orasida umumiy blacklist.

    Har bir bekor qilingan jti Redis kaliti sifatida saqlanadi
    (`revoked_token:<jti>`). Ixtiyoriy `ttl_seconds` berilsa kalit token
    muddati o'tgach avtomatik o'chadi — Redis'ni cheksiz shishishdan saqlaydi
    (token allaqachon eskirgach blacklist'da ushlab turishning ma'nosi yo'q).

    `redis` paketi yo'q yoki serverga ulanib bo'lmasa — yaratishda xato
    ko'taradi; fabrika buni ushlab in-memory'ga tushadi.
    """

    _KEY_PREFIX = "revoked_token:"

    def __init__(self, redis_url: str, ttl_seconds: int | None = None) -> None:
        if _redis is None:
            raise RuntimeError("redis paketi o'rnatilmagan — RedisTokenStore ishlatib bo'lmaydi")
        self._ttl_seconds = ttl_seconds
        self._client = _redis.Redis.from_url(redis_url, decode_responses=True)
        # Ulanishni darhol tekshiramiz: server yo'q bo'lsa hoziroq xato bersin,
        # keyinchalik logout paytida jimgina buzilmasin.
        self._client.ping()

    def _key(self, jti: str) -> str:
        return f"{self._KEY_PREFIX}{jti}"

    def revoke(self, jti: str) -> None:
        self._client.set(self._key(jti), "1", ex=self._ttl_seconds)

    def is_revoked(self, jti: str) -> bool:
        return self._client.exists(self._key(jti)) > 0


def _build_token_store() -> TokenRevocationStore:
    """Muhitga qarab mos do'konni tanlaydi.

    Xavfsiz default: redis paketi bor VA `redis_url` berilgan bo'lsa Redis'ga
    ulanishga urinadi; ulanish muvaffaqiyatsiz bo'lsa (server yo'q, import
    yo'q) in-memory'ga tushadi. Test muhitida esa har doim in-memory bo'lsin,
    aks holda testlar ishlaydigan Redis talab qilib qolardi.
    """
    if _redis is None or not settings.redis_url or settings.environment == "test":
        return InMemoryTokenStore()

    # Blacklist kaliti refresh token muddatidan uzoq turmasligi kerak
    # (eng uzoq yashaydigan token). Undan keyin token o'zi eskiradi.
    ttl_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
    try:
        return RedisTokenStore(settings.redis_url, ttl_seconds=ttl_seconds)
    except Exception:
        # Redis ulanmadi — ilovani yiqitmaymiz, in-memory'ga tushamiz.
        return InMemoryTokenStore()


# Modul darajasidagi yagona instansiya (singleton). `get_token_store()` orqali
# olingani uchun testlar `reset_token_store()` bilan uni almashtira oladi.
_token_store: TokenRevocationStore | None = None


def get_token_store() -> TokenRevocationStore:
    """Jarayon bo'yicha yagona token do'koni instansiyasini qaytaradi."""
    global _token_store
    if _token_store is None:
        _token_store = _build_token_store()
    return _token_store


def reset_token_store() -> None:
    """Do'kon holatini tozalaydi — testlar orasidagi izolyatsiya uchun.

    Keyingi `get_token_store()` chaqiruvi yangi (bo'sh) do'kon yaratadi.
    """
    global _token_store
    _token_store = None
