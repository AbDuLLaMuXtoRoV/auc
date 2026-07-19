"""PSP escrow provayder mantig'i testlari (create_hold / capture / release).

DB kerak emas — sof provider mantig'i, conftest fixture'siz ishlaydi.
"""

import pytest

from app.models.enums import PaymentStatus
from app.services.payment_providers import (
    BasePaymentProvider,
    FakeFailingProvider,
    MockPaymentProvider,
    PaymentProviderError,
)


def test_mock_create_hold_returns_held() -> None:
    result = MockPaymentProvider().create_hold(
        amount_tiyin=108000,
        currency="UZS",
        token_reference="tok_x",
        idempotency_key="k1",
    )
    assert result.status is PaymentStatus.HELD
    assert result.provider_payment_id.startswith("hold_")


def test_mock_capture_returns_released() -> None:
    provider = MockPaymentProvider()
    hold = provider.create_hold(
        amount_tiyin=108000,
        currency="UZS",
        token_reference="tok_x",
        idempotency_key="k1",
    )

    captured = provider.capture(provider_payment_id=hold.provider_payment_id, idempotency_key="k2")

    assert captured.status is PaymentStatus.RELEASED
    assert captured.provider_payment_id == hold.provider_payment_id


def test_mock_release_returns_cancelled_hold() -> None:
    provider = MockPaymentProvider()
    hold = provider.create_hold(
        amount_tiyin=108000,
        currency="UZS",
        token_reference="tok_x",
        idempotency_key="k1",
    )

    released = provider.release(provider_payment_id=hold.provider_payment_id, idempotency_key="k3")

    assert released.status is PaymentStatus.CANCELLED_HOLD
    assert released.provider_payment_id == hold.provider_payment_id


def test_failing_provider_create_hold_raises() -> None:
    with pytest.raises(PaymentProviderError):
        FakeFailingProvider().create_hold(
            amount_tiyin=108000,
            currency="UZS",
            token_reference="tok_x",
            idempotency_key="k1",
        )


def test_base_provider_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BasePaymentProvider()  # type: ignore[abstract]
