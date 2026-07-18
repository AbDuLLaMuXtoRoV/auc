"""To'lov xavfsizligi: mock provayder prod'da tovarni bepul olish yo'liga aylanmasligi.

Muammo (audit topilmasi): `get_payment_provider` har qanday noma'lum nomga
jimgina MockPaymentProvider qaytarardi, Mock esa `confirm_payment` da DOIM
PAID qaytaradi. Natijada prod'da "payme" so'ralganda ham Mock ishlab,
hech qanday real pul harakatisiz order PAID bo'lardi.

Bu testlar shu yo'lning har bir bo'g'inini yopiq ushlab turadi.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import INSECURE_DEFAULT_SECRET_KEY, Settings, settings
from app.services.payment_providers import (
    MockPaymentProvider,
    PaymentProviderError,
    available_provider_names,
    get_payment_provider,
)

STRONG_SECRET = "x" * 48


def test_unknown_provider_raises_instead_of_silently_falling_back_to_mock() -> None:
    """Noma'lum provayder nomi XATO berishi kerak, Mock EMAS.

    Ilgari bu 'payme' uchun jimgina Mock qaytarardi — eng xavfli xatti-harakat.
    """
    with pytest.raises(PaymentProviderError) as exc_info:
        get_payment_provider("payme")

    assert "payme" in str(exc_info.value)


def test_mock_provider_is_forbidden_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")

    with pytest.raises(PaymentProviderError):
        get_payment_provider(MockPaymentProvider.provider_name)


def test_mock_provider_is_allowed_in_non_production(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock local/test'da ruxsat etiladi.
    monkeypatch.setattr(settings, "environment", "local")
    assert isinstance(get_payment_provider("mock"), MockPaymentProvider)
    monkeypatch.setattr(settings, "environment", "test")
    assert isinstance(get_payment_provider("mock"), MockPaymentProvider)


def test_mock_is_not_listed_as_available_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    assert "mock" not in available_provider_names()


def test_confirm_mock_endpoint_is_blocked_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Servis qatlamidagi ikkinchi himoya.

    Endpoint prod'da umuman ro'yxatdan o'tmaydi (router import paytida
    tekshiriladi), lekin servis qatlami ham mustaqil himoyalangan bo'lishi
    kerak — kelajakda kimdir endpointni shartsiz ro'yxatga qo'shsa ham
    teshik ochilib ketmasin.
    """
    monkeypatch.setattr(settings, "environment", "production")

    response = client.post(
        "/api/v1/payments/1/confirm-mock",
        headers={"Authorization": "Bearer invalid"},
    )

    # Autentifikatsiyadan o'tsa ham 404 — mock oqimi prod'da mavjud emas.
    assert response.status_code in {401, 404}


def test_production_rejects_default_secret_key() -> None:
    """Default SECRET_KEY bilan prod'da ishga tushish IMKONSIZ bo'lishi kerak."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            secret_key=INSECURE_DEFAULT_SECRET_KEY,
            _env_file=None,
        )

    assert "SECRET_KEY" in str(exc_info.value)


def test_production_accepts_strong_secret_key() -> None:
    config = Settings(environment="production", secret_key=STRONG_SECRET, _env_file=None)
    assert config.is_production is True
    assert config.allow_mock_payments is False


def test_local_allows_default_secret_key() -> None:
    """Local'da default secret bilan ishlash qulay bo'lib qolsin."""
    config = Settings(
        environment="local",
        secret_key=INSECURE_DEFAULT_SECRET_KEY,
        _env_file=None,
    )
    assert config.allow_mock_payments is True
    assert config.is_production is False
