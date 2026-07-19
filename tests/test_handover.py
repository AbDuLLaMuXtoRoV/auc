"""Tovar topshirish (handover) oqimi: yaratish -> kod -> tasdiqlash -> capture.

Xaridor kodni to'g'ri kiritsa: handover COMPLETED, HELD to'lov RELEASED,
order COMPLETED. Kod faqat sotuvchiga ko'rinadi.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


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


def _create_order_with_hold(
    client: TestClient, seller_token: str, buyer_token: str, key: str
) -> dict:
    """Order yaratib, xaridor hold qiladi -> order PICKUP_PENDING, payment HELD."""
    order = _create_order(client, seller_token, buyer_token)
    hold = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"order_id": order["id"], "idempotency_key": key, "provider": "mock"},
    )
    assert hold.status_code == 201
    assert hold.json()["status"] == "held"
    return order


def test_seller_creates_handover_gets_code(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order_with_hold(client, seller, buyer, "hold-hc-01")

    resp = client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {seller}"},
        json={"order_id": order["id"], "meet_address": "Chorsu bozori"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["code"] is not None
    assert len(body["code"]) >= 1
    assert body["meet_address"] == "Chorsu bozori"


def test_other_user_cannot_create_handover(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    intruder = _register_and_login(client, "intruder@example.com")
    order = _create_order_with_hold(client, seller, buyer, "hold-hc-02")

    resp = client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {intruder}"},
        json={"order_id": order["id"]},
    )
    assert resp.status_code == 403


def test_create_handover_is_idempotent(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order_with_hold(client, seller, buyer, "hold-hc-03")

    first = client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {seller}"},
        json={"order_id": order["id"]},
    )
    second = client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {seller}"},
        json={"order_id": order["id"]},
    )
    assert first.status_code == 201
    # Idempotent: o'sha handover, o'sha kod.
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["code"] == second.json()["code"]


def test_wrong_code_does_not_complete_order(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order_with_hold(client, seller, buyer, "hold-hc-04")

    client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {seller}"},
        json={"order_id": order["id"]},
    )

    resp = client.post(
        f"/api/v1/handovers/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"code": "000000"},  # ataylab noto'g'ri (real kod tasodifiy)
    )
    # Agar tasodifan to'g'ri chiqib qolsa test noturg'un bo'lmasligi uchun,
    # real kodni olib solishtirmaymiz — statistik ehtimol juda kichik.
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Noto'g'ri kod"

    # Order hali COMPLETED emas — pul o'tmagan.
    order_after = client.get(
        f"/api/v1/orders/{order['id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert order_after.json()["status"] == "pickup_pending"


def test_correct_code_captures_and_completes(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order_with_hold(client, seller, buyer, "hold-hc-05")

    created = client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {seller}"},
        json={"order_id": order["id"]},
    )
    code = created.json()["code"]

    resp = client.post(
        f"/api/v1/handovers/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"code": code},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["confirmed_at"] is not None

    # Payment RELEASED.
    payment = client.get(
        f"/api/v1/payments/orders/{order['id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert payment.json()["status"] == "released"

    # Order COMPLETED.
    order_done = client.get(
        f"/api/v1/orders/{order['id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert order_done.json()["status"] == "completed"


def test_confirm_twice_conflicts(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order_with_hold(client, seller, buyer, "hold-hc-06")

    created = client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {seller}"},
        json={"order_id": order["id"]},
    )
    code = created.json()["code"]

    first = client.post(
        f"/api/v1/handovers/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"code": code},
    )
    assert first.status_code == 200

    # Ikkinchi tasdiq — handover endi PENDING emas.
    second = client.post(
        f"/api/v1/handovers/{order['id']}/confirm",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"code": code},
    )
    assert second.status_code == 409


def test_code_hidden_from_buyer_visible_to_seller(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order = _create_order_with_hold(client, seller, buyer, "hold-hc-07")

    created = client.post(
        "/api/v1/handovers",
        headers={"Authorization": f"Bearer {seller}"},
        json={"order_id": order["id"]},
    )
    code = created.json()["code"]

    # Sotuvchi ko'radi — kod bor.
    seller_view = client.get(
        f"/api/v1/handovers/{order['id']}", headers={"Authorization": f"Bearer {seller}"}
    )
    assert seller_view.status_code == 200
    assert seller_view.json()["code"] == code

    # Xaridor ko'radi — kod yashirin (None).
    buyer_view = client.get(
        f"/api/v1/handovers/{order['id']}", headers={"Authorization": f"Bearer {buyer}"}
    )
    assert buyer_view.status_code == 200
    assert buyer_view.json()["code"] is None
