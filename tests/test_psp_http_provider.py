"""Real HTTP PSP adapteri (HttpEscrowProvider) uchun unit testlar.

DB kerak emas — httpx.MockTransport orqali PSP javoblari simulyatsiya qilinadi.
Imzo (X-Signature) va idempotency sarlavhasi tekshiriladi.
"""

import json

import httpx
import pytest

from app.core.config import settings
from app.core.webhook import compute_signature
from app.models.enums import PaymentStatus
from app.services.payment_providers import (
    HttpEscrowProvider,
    PaymentProviderError,
    map_psp_status,
)

_API_KEY = "psp-secret-key"


def _provider(monkeypatch: pytest.MonkeyPatch, handler) -> HttpEscrowProvider:
    monkeypatch.setattr(settings, "psp_base_url", "https://psp.example")
    monkeypatch.setattr(settings, "psp_api_key", _API_KEY)
    return HttpEscrowProvider(transport=httpx.MockTransport(handler))


def test_unconfigured_base_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "psp_base_url", "")
    with pytest.raises(PaymentProviderError):
        HttpEscrowProvider()


def test_create_hold_signs_request_and_returns_held(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["sig"] = request.headers.get("X-Signature")
        captured["idem"] = request.headers.get("Idempotency-Key")
        captured["body"] = request.content
        return httpx.Response(200, json={"id": "hold_1", "status": "held"})

    provider = _provider(monkeypatch, handler)
    result = provider.create_hold(
        amount_tiyin=12960, currency="UZS", token_reference="tok_x", idempotency_key="idem-1"
    )

    assert result.status is PaymentStatus.HELD
    assert result.provider_payment_id == "hold_1"
    assert captured["path"] == "/v1/holds"
    assert captured["idem"] == "idem-1"
    # Imzo AYNAN yuborilgan baytlar ustida hisoblangan bo'lishi kerak.
    assert captured["sig"] == compute_signature(captured["body"], _API_KEY)
    assert json.loads(captured["body"])["amount"] == 12960


def test_capture_returns_released(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/holds/hold_1/capture"
        return httpx.Response(200, json={"id": "hold_1", "status": "released"})

    provider = _provider(monkeypatch, handler)
    result = provider.capture(provider_payment_id="hold_1", idempotency_key="cap-1")
    assert result.status is PaymentStatus.RELEASED
    assert result.provider_payment_id == "hold_1"


def test_release_returns_cancelled_hold(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/holds/hold_1/release"
        return httpx.Response(200, json={"id": "hold_1", "status": "cancelled_hold"})

    provider = _provider(monkeypatch, handler)
    result = provider.release(provider_payment_id="hold_1", idempotency_key="rel-1")
    assert result.status is PaymentStatus.CANCELLED_HOLD


def test_http_error_status_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="upstream down")

    provider = _provider(monkeypatch, handler)
    with pytest.raises(PaymentProviderError):
        provider.create_hold(
            amount_tiyin=1000, currency="UZS", token_reference=None, idempotency_key="k"
        )


def test_unknown_status_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "hold_1", "status": "teleported"})

    provider = _provider(monkeypatch, handler)
    with pytest.raises(PaymentProviderError):
        provider.create_hold(
            amount_tiyin=1000, currency="UZS", token_reference=None, idempotency_key="k"
        )


def test_network_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    provider = _provider(monkeypatch, handler)
    with pytest.raises(PaymentProviderError):
        provider.capture(provider_payment_id="hold_1", idempotency_key="k")


def test_status_map() -> None:
    assert map_psp_status("HELD") is PaymentStatus.HELD
    assert map_psp_status("released") is PaymentStatus.RELEASED
    assert map_psp_status("cancelled_hold") is PaymentStatus.CANCELLED_HOLD
    assert map_psp_status("failed") is PaymentStatus.FAILED
    assert map_psp_status("nonsense") is None
    assert map_psp_status(None) is None
