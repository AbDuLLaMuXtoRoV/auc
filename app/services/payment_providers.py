from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import uuid4

from app.core.config import settings
from app.models.enums import PaymentStatus


class PaymentProviderError(RuntimeError):
    """To'lov provayderini tanlash/ishlatishda konfiguratsiya xatosi."""


class PaymentProviderResult:
    def __init__(self, provider_payment_id: str, status: PaymentStatus) -> None:
        self.provider_payment_id = provider_payment_id
        self.status = status


class BasePaymentProvider(ABC):
    provider_name: str

    @abstractmethod
    def create_payment(self, *, amount: Decimal, currency: str) -> PaymentProviderResult:
        raise NotImplementedError

    @abstractmethod
    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        raise NotImplementedError


class MockPaymentProvider(BasePaymentProvider):
    """Faqat local/test uchun. Doim muvaffaqiyat qaytaradi — prod'da ISHLATILMAYDI.

    Bu provayder hech qanday real pul harakatini amalga oshirmaydi.
    Prod'da ochiq qolsa — xaridor tovarni bepul oladi.
    """

    provider_name = "mock"

    def create_payment(self, *, amount: Decimal, currency: str) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=f"mock_{uuid4().hex}",
            status=PaymentStatus.PENDING,
        )

    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=provider_payment_id,
            status=PaymentStatus.PAID,
        )


# Real provayderlar (Payme/Click/Uzum) shu registrga qo'shiladi.
# TODO: real PSP adapterlari — docs/PAYMENTS.md, Faza D.
_PROVIDERS: dict[str, type[BasePaymentProvider]] = {
    MockPaymentProvider.provider_name: MockPaymentProvider,
}


def available_provider_names() -> list[str]:
    """Joriy muhitda ruxsat etilgan provayder nomlari."""
    names = set(_PROVIDERS)
    if not settings.allow_mock_payments:
        names.discard(MockPaymentProvider.provider_name)
    return sorted(names)


def get_payment_provider(provider: str) -> BasePaymentProvider:
    """Nom bo'yicha to'lov provayderini qaytaradi.

    Noma'lum nom uchun XATO beradi. Ilgari bu funksiya har qanday nomga
    jimgina Mock qaytarardi — ya'ni prod'da "payme" so'ralganda ham Mock
    ishlab, to'lov haqiqatda amalga oshmasa ham PAID bo'lardi.

    :raises PaymentProviderError: nom noma'lum yoki bu muhitda taqiqlangan.
    """
    provider_cls = _PROVIDERS.get(provider)
    if provider_cls is None:
        raise PaymentProviderError(
            f"Noma'lum to'lov provayderi: {provider!r}. "
            f"Mavjudlari: {available_provider_names()}"
        )

    if provider_cls is MockPaymentProvider and not settings.allow_mock_payments:
        raise PaymentProviderError(
            f"Mock to'lov provayderi '{settings.environment}' muhitida TAQIQLANGAN."
        )

    return provider_cls()
