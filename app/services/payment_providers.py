from abc import ABC, abstractmethod
from uuid import uuid4

from app.core.config import settings
from app.models.enums import PaymentStatus
from app.money import Tiyin


class PaymentProviderError(RuntimeError):
    """To'lov provayderini tanlash/ishlatishda konfiguratsiya xatosi."""


class PaymentProviderResult:
    def __init__(self, provider_payment_id: str, status: PaymentStatus) -> None:
        self.provider_payment_id = provider_payment_id
        self.status = status


class BasePaymentProvider(ABC):
    provider_name: str

    @abstractmethod
    def create_payment(self, *, amount: Tiyin, currency: str) -> PaymentProviderResult:
        raise NotImplementedError

    @abstractmethod
    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        raise NotImplementedError

    @abstractmethod
    def create_hold(
        self,
        *,
        amount_tiyin: Tiyin,
        currency: str,
        token_reference: str | None,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        """Escrow: xaridor kartasida mablag'ni bloklaydi (hold), pul hali ko'chmaydi.

        Natija status=HELD. Bu bosqichda pul PSP tomonida "muzlatilgan" —
        na sotuvchida, na bizda. Keyin capture yoki release chaqiriladi.
        """
        raise NotImplementedError

    @abstractmethod
    def capture(
        self,
        *,
        provider_payment_id: str,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        """Escrow: bloklangan mablag'ni yechib, sotuvchiga o'tkazadi.

        Natija status=RELEASED. Faqat oldindan HELD bo'lgan hold ustida ishlaydi.
        """
        raise NotImplementedError

    @abstractmethod
    def release(
        self,
        *,
        provider_payment_id: str,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        """Escrow: blokni bekor qiladi — pul xaridorda qoladi.

        Natija status=CANCELLED_HOLD. Bitim bekor bo'lganda ishlatiladi.
        """
        raise NotImplementedError


class MockPaymentProvider(BasePaymentProvider):
    """Faqat local/test uchun. Doim muvaffaqiyat qaytaradi — prod'da ISHLATILMAYDI.

    Bu provayder hech qanday real pul harakatini amalga oshirmaydi.
    Prod'da ochiq qolsa — xaridor tovarni bepul oladi.
    """

    provider_name = "mock"

    def create_payment(self, *, amount: Tiyin, currency: str) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=f"mock_{uuid4().hex}",
            status=PaymentStatus.PENDING,
        )

    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=provider_payment_id,
            status=PaymentStatus.PAID,
        )

    def create_hold(
        self,
        *,
        amount_tiyin: Tiyin,
        currency: str,
        token_reference: str | None,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=f"hold_{uuid4().hex}",
            status=PaymentStatus.HELD,
        )

    def capture(
        self,
        *,
        provider_payment_id: str,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=provider_payment_id,
            status=PaymentStatus.RELEASED,
        )

    def release(
        self,
        *,
        provider_payment_id: str,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=provider_payment_id,
            status=PaymentStatus.CANCELLED_HOLD,
        )


class FakeFailingProvider(BasePaymentProvider):
    """Faqat test uchun: escrow xatolarini simulyatsiya qiladi.

    Registrga QO'SHILMAYDI — get_payment_provider orqali olinmaydi.
    create_hold har doim PaymentProviderError ko'taradi, shunda escrow
    xato yo'lini (hold ololmaslik) test qilish mumkin.
    """

    provider_name = "fake_failing"

    def create_payment(self, *, amount: Tiyin, currency: str) -> PaymentProviderResult:
        raise PaymentProviderError("FakeFailingProvider: create_payment ataylab muvaffaqiyatsiz.")

    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        raise PaymentProviderError("FakeFailingProvider: confirm_payment ataylab muvaffaqiyatsiz.")

    def create_hold(
        self,
        *,
        amount_tiyin: Tiyin,
        currency: str,
        token_reference: str | None,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        raise PaymentProviderError("FakeFailingProvider: hold yaratib bo'lmadi (simulyatsiya).")

    def capture(
        self,
        *,
        provider_payment_id: str,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        raise PaymentProviderError("FakeFailingProvider: capture muvaffaqiyatsiz (simulyatsiya).")

    def release(
        self,
        *,
        provider_payment_id: str,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        raise PaymentProviderError("FakeFailingProvider: release muvaffaqiyatsiz (simulyatsiya).")


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
            f"Noma'lum to'lov provayderi: {provider!r}. Mavjudlari: {available_provider_names()}"
        )

    if provider_cls is MockPaymentProvider and not settings.allow_mock_payments:
        raise PaymentProviderError(
            f"Mock to'lov provayderi '{settings.environment}' muhitida TAQIQLANGAN."
        )

    return provider_cls()
