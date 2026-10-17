from abc import ABC, abstractmethod
from uuid import uuid4

from app.core.config import settings
from app.core.webhook import compute_signature
from app.models.enums import PaymentStatus
from app.money import Tiyin


class PaymentProviderError(RuntimeError):
    """To'lov provayderini tanlash/ishlatishda konfiguratsiya yoki tarmoq xatosi."""


# PSP javobidagi status matnini bizning enum'ga xaritalash. Haqiqat manbai —
# PSP holati; noma'lum status = xato (jimgina noto'g'ri holatga o'tmaymiz).
_PSP_STATUS_MAP: dict[str, PaymentStatus] = {
    "pending": PaymentStatus.PENDING,
    "authorized": PaymentStatus.HELD,
    "held": PaymentStatus.HELD,
    "hold": PaymentStatus.HELD,
    "captured": PaymentStatus.RELEASED,
    "released": PaymentStatus.RELEASED,
    "cancelled": PaymentStatus.CANCELLED_HOLD,
    "canceled": PaymentStatus.CANCELLED_HOLD,
    "cancelled_hold": PaymentStatus.CANCELLED_HOLD,
    "voided": PaymentStatus.CANCELLED_HOLD,
    "failed": PaymentStatus.FAILED,
    "declined": PaymentStatus.FAILED,
}


def map_psp_status(raw: str | None) -> PaymentStatus | None:
    """PSP status matnini PaymentStatus'ga aylantiradi (topilmasa None)."""
    if not raw:
        return None
    return _PSP_STATUS_MAP.get(raw.strip().lower())


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


class HttpEscrowProvider(BasePaymentProvider):
    """Real PSP escrow adapteri — HTTP orqali hold/capture/release.

    Vendor-neytral REST shartnomasi (Payme/Click/Uzum/Octo shu interfeys
    ortiga ulanadi):
        POST {base}/v1/holds                 -> {id, status}
        POST {base}/v1/holds/{id}/capture    -> {id, status}
        POST {base}/v1/holds/{id}/release    -> {id, status}

    Har so'rov tanasi HMAC-SHA256 bilan imzolanadi (X-Signature) — PSP so'rov
    haqiqatan bizdan kelganini tekshiradi (webhook imzosining teskari yo'nalishi).
    `Idempotency-Key` uzatiladi: tarmoq retry'sida PSP ikki marta hold qilmaydi.

    Sozlama bo'sh (`psp_base_url`) bo'lsa — instansiya YARATILMAYDI (aniq config
    xatosi), Mock singari. Shu sabab prod'da "psp" so'ralsa-yu sozlanmagan bo'lsa
    jimgina noto'g'ri to'lov bo'lmaydi.
    """

    provider_name = "psp"

    def __init__(self, *, transport=None) -> None:
        # transport — faqat test uchun (httpx.MockTransport). Prod'da None.
        self._transport = transport
        self.base_url = settings.psp_base_url.rstrip("/")
        self.api_key = settings.psp_api_key
        self.timeout = settings.psp_timeout_seconds
        if not self.base_url:
            raise PaymentProviderError(
                "PSP adapteri sozlanmagan: PSP_BASE_URL bo'sh. .env orqali bering."
            )

    # --- Escrow (asosiy oqim) ------------------------------------------------

    def create_hold(
        self,
        *,
        amount_tiyin: Tiyin,
        currency: str,
        token_reference: str | None,
        idempotency_key: str,
    ) -> PaymentProviderResult:
        data = self._post(
            "/v1/holds",
            {
                "amount": int(amount_tiyin),
                "currency": currency,
                "token_reference": token_reference,
                "idempotency_key": idempotency_key,
            },
            idempotency_key=idempotency_key,
        )
        return self._result(data, expected=PaymentStatus.HELD)

    def capture(self, *, provider_payment_id: str, idempotency_key: str) -> PaymentProviderResult:
        data = self._post(
            f"/v1/holds/{provider_payment_id}/capture",
            {"idempotency_key": idempotency_key},
            idempotency_key=idempotency_key,
        )
        return self._result(data, expected=PaymentStatus.RELEASED, fallback_id=provider_payment_id)

    def release(self, *, provider_payment_id: str, idempotency_key: str) -> PaymentProviderResult:
        data = self._post(
            f"/v1/holds/{provider_payment_id}/release",
            {"idempotency_key": idempotency_key},
            idempotency_key=idempotency_key,
        )
        return self._result(
            data, expected=PaymentStatus.CANCELLED_HOLD, fallback_id=provider_payment_id
        )

    # --- Eski intent oqimi (escrow'da ishlatilmaydi) -------------------------

    def create_payment(self, *, amount: Tiyin, currency: str) -> PaymentProviderResult:
        raise PaymentProviderError(
            "HttpEscrowProvider intent oqimini qo'llamaydi — hold ishlating."
        )

    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        raise PaymentProviderError(
            "HttpEscrowProvider intent oqimini qo'llamaydi — capture ishlating."
        )

    # --- Ichki yordamchilar --------------------------------------------------

    def _post(self, path: str, payload: dict, *, idempotency_key: str) -> dict:
        """Imzolangan JSON POST. Tarmoq/HTTP xatosi -> PaymentProviderError."""
        import json

        import httpx

        # Imzo AYNAN yuboriladigan baytlar ustida — qayta serializatsiya qilinmaydi.
        body = json.dumps(payload, separators=(",", ":")).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Signature": compute_signature(body, self.api_key),
            "Idempotency-Key": idempotency_key,
        }
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=self.timeout, transport=self._transport
            ) as http:
                response = http.post(path, content=body, headers=headers)
        except httpx.HTTPError as exc:
            raise PaymentProviderError(f"PSP so'rovi muvaffaqiyatsiz: {exc}") from exc

        if response.status_code >= 400:
            raise PaymentProviderError(
                f"PSP {response.status_code} qaytardi: {response.text[:200]}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise PaymentProviderError("PSP javobi JSON emas") from exc
        if not isinstance(data, dict):
            raise PaymentProviderError("PSP javobi obyekt emas")
        return data

    def _result(
        self,
        data: dict,
        *,
        expected: PaymentStatus,
        fallback_id: str | None = None,
    ) -> PaymentProviderResult:
        """PSP javobidan (id, status) ni oladi va statusni tekshiradi."""
        provider_payment_id = data.get("id") or data.get("provider_payment_id") or fallback_id
        if not provider_payment_id:
            raise PaymentProviderError("PSP javobida hold id yo'q")
        status = map_psp_status(data.get("status"))
        if status is None:
            raise PaymentProviderError(f"PSP noma'lum status qaytardi: {data.get('status')!r}")
        # PSP kutilmagan holat qaytarsa (masalan hold so'radik, u failed dedi) —
        # o'sha haqiqiy statusni qaytaramiz; chaqiruvchi state machine tekshiradi.
        _ = expected
        return PaymentProviderResult(provider_payment_id=str(provider_payment_id), status=status)


# Registr: Mock (faqat local/test guard bilan) + real HTTP PSP adapteri.
# HttpEscrowProvider sozlanmagan bo'lsa instansiyalashda aniq xato beradi.
_PROVIDERS: dict[str, type[BasePaymentProvider]] = {
    MockPaymentProvider.provider_name: MockPaymentProvider,
    HttpEscrowProvider.provider_name: HttpEscrowProvider,
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
