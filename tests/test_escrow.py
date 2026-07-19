"""Escrow oqimi: hold -> capture/release, idempotentlik, webhook imzo, audit.

Pul harakati bilan bog'liq eng nozik qism. Har o'zgarish test talab qiladi.
"""

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.webhook import compute_signature
from app.models.audit_log import AuditLog
from app.models.payment import Payment


def _register_and_login(client: TestClient, email: str) -> str:
    password = "Password1"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _create_order(client: TestClient, seller_token: str, buyer_token: str) -> dict:
    """Auksion -> bid -> close orqali order yaratadi (final_price = 12000)."""
    item = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"title": "Lens", "condition": "used", "starting_price": "10000"},
    )
    assert item.status_code == 201
    now = datetime.now(UTC)
    auction = client.post(
        "/api/v1/auctions",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "item_id": item.json()["id"],
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "minimum_bid_increment": "1000",
        },
    )
    auction_id = auction.json()["id"]
    client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"amount": "12000"},
    )
    client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    orders = client.get("/api/v1/orders/buyer", headers={"Authorization": f"Bearer {buyer_token}"})
    return orders.json()[0]


def test_hold_capture_flow_and_premium(client: TestClient, db_session: Session) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order(client, seller, buyer)

    hold = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": order["id"], "idempotency_key": "hold-key-0001", "provider": "mock"},
    )
    assert hold.status_code == 201
    body = hold.json()
    assert body["status"] == "held"
    # Buyer premium 8%: 12000 * 800 // 10000 = 960; total = 12960.
    assert body["amount"] == "12000"
    assert body["premium"] == "960"
    assert body["total"] == "12960"
    payment_id = body["id"]

    # Order hold'dan keyin pickup_pending.
    order_after = client.get(
        f"/api/v1/orders/{order['id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert order_after.json()["status"] == "pickup_pending"

    # Capture -> released, order completed.
    cap = client.post(
        f"/api/v1/payments/{payment_id}/capture",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"idempotency_key": "cap-key-0001"},
    )
    assert cap.status_code == 200
    assert cap.json()["status"] == "released"

    order_done = client.get(
        f"/api/v1/orders/{order['id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert order_done.json()["status"] == "completed"

    # Audit: PAYMENT_HELD va PAYMENT_RELEASED yozilgan.
    actions = {
        a.action for a in db_session.query(AuditLog).filter(AuditLog.entity_id == payment_id).all()
    }
    assert {"PAYMENT_HELD", "PAYMENT_RELEASED"} <= actions


def test_hold_is_idempotent(client: TestClient, db_session: Session) -> None:
    """Bir xil idempotency_key -> bitta hold, ikki marta bloklanmaydi."""
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order(client, seller, buyer)

    payload = {"order_id": order["id"], "idempotency_key": "dup-key-0001", "provider": "mock"}
    first = client.post(
        "/api/v1/payments/holds", headers={"Authorization": f"Bearer {buyer}"}, json=payload
    )
    second = client.post(
        "/api/v1/payments/holds", headers={"Authorization": f"Bearer {buyer}"}, json=payload
    )
    assert first.status_code == 201
    assert first.json()["id"] == second.json()["id"]  # o'sha payment

    count = db_session.query(Payment).filter(Payment.order_id == order["id"]).count()
    assert count == 1  # ikkinchi hold yaratilmadi


def test_double_capture_is_idempotent(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order(client, seller, buyer)

    hold = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": order["id"], "idempotency_key": "hold-key-2", "provider": "mock"},
    )
    pid = hold.json()["id"]
    c1 = client.post(
        f"/api/v1/payments/{pid}/capture",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"idempotency_key": "cap-key-20"},
    )
    c2 = client.post(
        f"/api/v1/payments/{pid}/capture",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"idempotency_key": "cap-key-2b"},
    )
    assert c1.json()["status"] == "released"
    assert c2.status_code == 200
    assert c2.json()["status"] == "released"  # o'zgarmadi


def test_release_hold_cancels_order(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order(client, seller, buyer)

    hold = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": order["id"], "idempotency_key": "hold-key-3", "provider": "mock"},
    )
    pid = hold.json()["id"]
    rel = client.post(
        f"/api/v1/payments/{pid}/release",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"idempotency_key": "rel-key-30"},
    )
    assert rel.status_code == 200
    assert rel.json()["status"] == "cancelled_hold"

    order_after = client.get(
        f"/api/v1/orders/{order['id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert order_after.json()["status"] == "cancelled"


def test_other_user_cannot_capture(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    intruder = _register_and_login(client, "intruder@example.com")
    order = _create_order(client, seller, buyer)

    hold = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": order["id"], "idempotency_key": "hold-key-4", "provider": "mock"},
    )
    pid = hold.json()["id"]
    r = client.post(
        f"/api/v1/payments/{pid}/capture",
        headers={"Authorization": f"Bearer {intruder}"},
        json={"idempotency_key": "cap-key-40"},
    )
    assert r.status_code == 403


def test_webhook_rejects_missing_signature(client: TestClient) -> None:
    r = client.post("/api/v1/payments/webhooks/psp", content=b'{"event":"x"}')
    assert r.status_code == 401


def test_webhook_rejects_bad_signature(client: TestClient) -> None:
    r = client.post(
        "/api/v1/payments/webhooks/psp",
        content=b'{"event":"x"}',
        headers={"x-signature": "deadbeef"},
    )
    assert r.status_code == 401


def test_webhook_accepts_valid_signature(client: TestClient) -> None:
    raw = json.dumps({"event": "capture", "id": "hold_x"}).encode()
    sig = compute_signature(raw, settings.psp_webhook_secret)
    r = client.post(
        "/api/v1/payments/webhooks/psp",
        content=raw,
        headers={"x-signature": sig},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}
