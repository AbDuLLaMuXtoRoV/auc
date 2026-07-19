"""Nizo (dispute) oqimi: xaridor HELD hold ustidan nizo ochadi, admin hal
qiladi (buyer -> release, seller -> capture).

Pul harakati bilan bog'liq — har ssenariy payment/order holatini tekshiradi.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import AuthenticatedUser


def _held_order(client: TestClient, seller_token: str, buyer_token: str, key: str) -> dict:
    """Auksion -> bid -> close -> order -> hold. Payment HELD holatida
    order qaytaradi. `dict`: {"order_id", "payment_id"}."""
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
    order = orders.json()[0]

    hold = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"order_id": order["id"], "idempotency_key": key, "provider": "mock"},
    )
    assert hold.status_code == 201, hold.text
    assert hold.json()["status"] == "held"
    return {"order_id": order["id"], "payment_id": hold.json()["id"]}


def _register_and_login(client: TestClient, email: str) -> str:
    password = "Password1"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def test_buyer_opens_dispute_on_held_order(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-01")

    resp = client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "damaged", "description": "singan"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "open"
    assert body["reason"] == "damaged"
    assert body["order_id"] == ctx["order_id"]


def test_non_buyer_cannot_open_dispute(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    intruder = _register_and_login(client, "intruder@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-02")

    for token in (seller, intruder):
        resp = client.post(
            "/api/v1/disputes",
            headers={"Authorization": f"Bearer {token}"},
            json={"order_id": ctx["order_id"], "reason": "fake"},
        )
        assert resp.status_code == 403, resp.text


def test_second_open_dispute_conflicts(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-03")

    first = client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "not_received"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "damaged"},
    )
    assert second.status_code == 409, second.text


def test_admin_resolves_for_seller_captures(
    client: TestClient, db_session: Session, test_admin: AuthenticatedUser
) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-04")

    disp = client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "other"},
    )
    dispute_id = disp.json()["id"]

    resolved = client.post(
        f"/api/v1/disputes/{dispute_id}/resolve",
        headers=test_admin.headers,
        json={"decision": "seller", "resolution": "dalil sotuvchi foydasiga"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved_seller"

    payment = client.get(
        f"/api/v1/payments/orders/{ctx['order_id']}",
        headers={"Authorization": f"Bearer {buyer}"},
    )
    assert payment.json()["status"] == "released"

    order = client.get(
        f"/api/v1/orders/{ctx['order_id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert order.json()["status"] == "completed"


def test_admin_resolves_for_buyer_releases(
    client: TestClient, test_admin: AuthenticatedUser
) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-05")

    disp = client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "not_as_described"},
    )
    dispute_id = disp.json()["id"]

    resolved = client.post(
        f"/api/v1/disputes/{dispute_id}/resolve",
        headers=test_admin.headers,
        json={"decision": "buyer", "resolution": "dalil xaridor foydasiga"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved_buyer"

    payment = client.get(
        f"/api/v1/payments/orders/{ctx['order_id']}",
        headers={"Authorization": f"Bearer {buyer}"},
    )
    assert payment.json()["status"] == "cancelled_hold"

    order = client.get(
        f"/api/v1/orders/{ctx['order_id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert order.json()["status"] == "cancelled"


def test_non_admin_cannot_resolve(client: TestClient, db_session: Session) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-06")

    disp = client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "damaged"},
    )
    dispute_id = disp.json()["id"]

    # Xaridorning o'zi ham hal qilolmaydi.
    resp = client.post(
        f"/api/v1/disputes/{dispute_id}/resolve",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"decision": "seller", "resolution": "o'zim"},
    )
    assert resp.status_code == 403, resp.text


def test_opener_can_read_dispute_intruder_cannot(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    intruder = _register_and_login(client, "intruder@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-07")

    disp = client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "fake"},
    )
    dispute_id = disp.json()["id"]

    ok = client.get(f"/api/v1/disputes/{dispute_id}", headers={"Authorization": f"Bearer {buyer}"})
    assert ok.status_code == 200

    forbidden = client.get(
        f"/api/v1/disputes/{dispute_id}", headers={"Authorization": f"Bearer {intruder}"}
    )
    assert forbidden.status_code == 403


def test_admin_open_queue_lists_open_disputes(
    client: TestClient, test_admin: AuthenticatedUser
) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    ctx = _held_order(client, seller, buyer, key="hold-disp-08")

    client.post(
        "/api/v1/disputes",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": ctx["order_id"], "reason": "damaged"},
    )

    queue = client.get("/api/v1/disputes?status=open", headers=test_admin.headers)
    assert queue.status_code == 200
    assert len(queue.json()) == 1
    assert queue.json()[0]["status"] == "open"
