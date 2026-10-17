"""SMS provayderi — ulanadigan abstraksiya (push_provider naqshi).

OTP kodini SMS orqali yetkazish uchun YAGONA interfeys. Hozir faqat log
provayderi bor (`LogSmsProvider`) — kod log'ga yoziladi, real tarmoq chaqiruvi
yo'q (local/test). Real O'zbekiston provayderlari (Eskiz, Play Mobile va h.k.)
keyin shu registrga qo'shiladi.

Graceful: noma'lum provayder nomi ilovani yiqitmaydi — log provayderiga
tushib, ogohlantirish yoziladi. Shunda SMS jimgina yo'qolmaydi (kod hech
bo'lmasa log'da qoladi) va OTP oqimi ishlashda davom etadi.
"""

import logging
from abc import ABC, abstractmethod
from uuid import uuid4

from app.core.config import settings

logger = logging.getLogger(__name__)


class SmsResult:
    """SMS yuborish natijasi.

    :param message_id: provayder bergan xabar identifikatori (audit/kuzatuv uchun).
    :param delivered: xabar yetkazishga topshirildimi.
    """

    def __init__(self, message_id: str, delivered: bool) -> None:
        self.message_id = message_id
        self.delivered = delivered


class BaseSmsProvider(ABC):
    """SMS provayderlari uchun umumiy shartnoma."""

    provider_name: str

    @abstractmethod
    def send(self, phone: str, text: str) -> SmsResult:
        """Berilgan raqamga SMS matnini yuboradi.

        :param phone: qabul qiluvchi telefon raqami (E.164, masalan +998901234567).
        :param text: SMS matni (OTP kodi bilan).
        """
        raise NotImplementedError


class LogSmsProvider(BaseSmsProvider):
    """Local/test uchun: SMS haqiqatan yuborilmaydi, faqat log'ga yoziladi.

    Doim delivered=True qaytaradi. Real provayder o'rniga ishlatiladi —
    tashqi tarmoq chaqiruvi yo'q.
    """

    provider_name = "log"

    def send(self, phone: str, text: str) -> SmsResult:
        message_id = f"log_{uuid4().hex}"
        logger.info("sms[%s] -> phone=%s text=%r", message_id, phone, text)
        return SmsResult(message_id=message_id, delivered=True)


class NullSmsProvider(BaseSmsProvider):
    """SMS'ni butunlay o'chiruvchi provayder: hech narsa yubormaydi.

    delivered=False qaytaradi — kanal mavjud, lekin faol emas holatida.
    """

    provider_name = "null"

    def send(self, phone: str, text: str) -> SmsResult:
        return SmsResult(message_id=f"null_{uuid4().hex}", delivered=False)


# Real provayderlar (Eskiz, Play Mobile) shu registrga qo'shiladi.
_PROVIDERS: dict[str, type[BaseSmsProvider]] = {
    LogSmsProvider.provider_name: LogSmsProvider,
    NullSmsProvider.provider_name: NullSmsProvider,
}


def available_provider_names() -> list[str]:
    """Ro'yxatga olingan SMS provayder nomlari."""
    return sorted(_PROVIDERS)


def get_sms_provider(name: str | None = None) -> BaseSmsProvider:
    """Nom bo'yicha SMS provayderini qaytaradi (default: settings.sms_provider).

    Graceful: noma'lum nom uchun XATO ko'tarilmaydi — log provayderiga tushadi
    va ogohlantirish yoziladi. Real provayder hali ulanmagan bosqichda
    (masalan sms_provider="eskiz") OTP oqimi to'xtab qolmasligi uchun.
    """
    provider_key = name or settings.sms_provider
    provider_cls = _PROVIDERS.get(provider_key)
    if provider_cls is None:
        logger.warning(
            "Noma'lum SMS provayderi: %r. Log provayderiga tushildi. Mavjudlari: %s",
            provider_key,
            available_provider_names(),
        )
        provider_cls = LogSmsProvider
    return provider_cls()
