"""Token bekor qilish do'koni (logout blacklist) testlari.

Ikki narsani isbotlaydi:
  * `InMemoryTokenStore` interfeysi (revoke/is_revoked/reset) to'g'ri ishlaydi;
  * `security.py` do'konga ulangach eski logout xatti-harakati AYNAN saqlanadi
    (revoke qilingan token endi decode bo'lmaydi).

Redis testi ixtiyoriy: `redis` paketi bo'lmasa `importorskip` bilan
o'tkazib yuboriladi. Butun to'plam Redis'siz ham yashil bo'ladi (in-memory
default).
"""

import pytest

from app.core import security
from app.core.token_store import (
    InMemoryTokenStore,
    TokenRevocationStore,
    get_token_store,
    reset_token_store,
)


def test_inmemory_revoke_and_check() -> None:
    store = InMemoryTokenStore()
    assert store.is_revoked("jti-1") is False
    store.revoke("jti-1")
    assert store.is_revoked("jti-1") is True
    # Boshqa jti ta'sirlanmaydi.
    assert store.is_revoked("jti-2") is False


def test_inmemory_reset_clears_state() -> None:
    store = InMemoryTokenStore()
    store.revoke("jti-1")
    store._revoked.clear()
    assert store.is_revoked("jti-1") is False


def test_get_token_store_is_singleton() -> None:
    reset_token_store()
    first = get_token_store()
    second = get_token_store()
    assert first is second
    assert isinstance(first, TokenRevocationStore)


def test_reset_token_store_replaces_instance() -> None:
    first = get_token_store()
    first.revoke("jti-reset")
    assert first.is_revoked("jti-reset") is True
    reset_token_store()
    second = get_token_store()
    # Yangi bo'sh do'kon — eski bekor qilish yo'qoladi.
    assert second is not first
    assert second.is_revoked("jti-reset") is False


def test_security_revoke_token_blocks_decode() -> None:
    """Eski xatti-harakat: revoke'dan keyin decode None qaytaradi."""
    reset_token_store()
    token = security.create_access_token("user-123")

    # Bekor qilinmagan token normal decode bo'ladi.
    payload = security.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"

    # Logout: token bekor qilinadi.
    assert security.revoke_token(token) is True

    # Endi o'sha token qabul qilinmaydi.
    assert security.decode_access_token(token) is None
    assert security.decode_token(token) is None

    reset_token_store()


def test_security_revoke_invalid_token_returns_false() -> None:
    reset_token_store()
    assert security.revoke_token("not-a-jwt") is False


def test_redis_store_optional() -> None:
    """Redis paketi bo'lsa import bo'ladi; bo'lmasa test o'tkazib yuboriladi."""
    redis = pytest.importorskip("redis")
    from app.core.token_store import RedisTokenStore

    # Ulanmaydigan manzil — yaratishda ulanish xatosi kutamiz (server yo'q).
    with pytest.raises(redis.exceptions.RedisError):
        RedisTokenStore("redis://127.0.0.1:6390/0")
