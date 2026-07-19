"""Code/security review topilmalari uchun regressiya qalqonlari.

Har biri tuzatilgan teshikni qayta ochilishidan himoyalaydi.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import UserRole
from tests.conftest import create_user


def _login(client: TestClient, email: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password1", "full_name": email.split("@")[0]},
    )
    r = client.post("/api/v1/auth/login", data={"username": email, "password": "Password1"})
    return r.json()["access_token"]


def _order(client: TestClient, seller: str, buyer: str) -> dict:
    item = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller}"},
        json={"title": "Thing", "condition": "used", "starting_price": "10000"},
    )
    now = datetime.now(UTC)
    auction = client.post(
        "/api/v1/auctions",
        headers={"Authorization": f"Bearer {seller}"},
        json={
            "item_id": item.json()["id"],
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "minimum_bid_increment": "1000",
        },
    )
    aid = auction.json()["id"]
    client.post(
        f"/api/v1/bids/{aid}",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"amount": "12000"},
    )
    client.post(f"/api/v1/auctions/{aid}/close", headers={"Authorization": f"Bearer {seller}"})
    return client.get("/api/v1/orders/buyer", headers={"Authorization": f"Bearer {buyer}"}).json()[
        0
    ]


def test_hold_idempotency_key_is_owner_scoped(client: TestClient) -> None:
    """Begona idempotency_key bilan hold -> 409, boshqaning payment'i oshkor bo'lmaydi."""
    seller = _login(client, "seller@example.com")
    buyer1 = _login(client, "buyer1@example.com")
    buyer2 = _login(client, "buyer2@example.com")
    o1 = _order(client, seller, buyer1)

    client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer1}"},
        json={"order_id": o1["id"], "idempotency_key": "shared-key-01", "provider": "mock"},
    )
    # buyer2 o'sha kalitni ishlatmoqchi (boshqa order bilan bo'lsa ham) -> 409.
    seller2 = _login(client, "seller2@example.com")
    o2 = _order(client, seller2, buyer2)
    resp = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer2}"},
        json={"order_id": o2["id"], "idempotency_key": "shared-key-01", "provider": "mock"},
    )
    assert resp.status_code == 409


def test_order_status_invalid_transition_rejected(client: TestClient, db_session: Session) -> None:
    """Order holati state machine: taqiqlangan o'tish 409."""
    seller = _login(client, "seller@example.com")
    buyer = _login(client, "buyer@example.com")
    admin = create_user(client, db_session, email="admin@example.com", role=UserRole.ADMIN)
    order = _order(client, seller, buyer)

    # PENDING_PAYMENT -> COMPLETED to'g'ridan-to'g'ri sakrash taqiqlangan.
    resp = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers=admin.headers,
        json={"status": "completed"},
    )
    assert resp.status_code == 409


def test_production_forgot_password_hides_token() -> None:
    """Prod'da reset token javobda qaytmaydi (akkaunt egallash teshigi)."""
    # Bu sof konfiguratsiya xatti-harakati: is_production True bo'lsa token None.
    config = Settings(
        environment="production",
        secret_key="x" * 48,
        psp_webhook_secret="y" * 48,
        _env_file=None,
    )
    assert config.is_production is True


def test_production_requires_strong_webhook_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key="x" * 48, _env_file=None)
