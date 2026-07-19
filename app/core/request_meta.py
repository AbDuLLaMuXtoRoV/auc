"""So'rovdan mijoz metama'lumotini olish (IP, qurilma) — anti-fraud/audit uchun."""

import ipaddress

from fastapi import Request


def client_ip(request: Request) -> str | None:
    """Mijoz IP'sini qaytaradi — faqat haqiqiy IP bo'lsa.

    INET ustunlarga yoziladi. TestClient yoki noto'g'ri host ("testclient")
    Postgres DataError beradi, shuning uchun validatsiya qilinadi.
    """
    if request.client is None:
        return None
    host = request.client.host
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host


def device_id(request: Request) -> str | None:
    """Mijoz qurilma identifikatori (X-Device-Id sarlavhasi). Ixtiyoriy."""
    value = request.headers.get("x-device-id")
    if value is None:
        return None
    return value[:128]
