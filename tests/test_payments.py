from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str) -> str:
    password = "Password1"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _create_order(client: TestClient, seller_token: str, buyer_token: str) -> dict:
    item_response = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "title": "Laser level",
            "condition": "used",
            "starting_price": "10000",
        },
    )
    assert item_response.status_code == 201

    now = datetime.now(UTC)
    auction_response = client.post(
        "/api/v1/auctions",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "item_id": item_response.json()["id"],
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "minimum_bid_increment": "1000",
        },
    )
    assert auction_response.status_code == 201
    auction_id = auction_response.json()["id"]

    bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"amount": "12000"},
    )
    assert bid_response.status_code == 201

    close_response = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert close_response.status_code == 200

    orders_response = client.get(
        "/api/v1/orders/buyer",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert orders_response.status_code == 200
    orders = orders_response.json()
    assert len(orders) == 1
    return orders[0]


def test_create_and_confirm_payment_updates_order_status(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    buyer_token = _register_and_login(client, "buyer@example.com")
    order = _create_order(client, seller_token, buyer_token)

    payment_response = client.post(
        "/api/v1/payments/intents",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "order_id": order["id"],
            "amount": order["final_price"],
            "currency": "UZS",
            "provider": "mock",
        },
    )
    assert payment_response.status_code == 201
    payment = payment_response.json()
    assert payment["status"] == "pending"
    assert payment["provider"] == "mock"
    assert payment["provider_payment_id"].startswith("mock_")

    by_order_response = client.get(
        f"/api/v1/payments/orders/{order['id']}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert by_order_response.status_code == 200
    assert by_order_response.json()["id"] == payment["id"]

    confirm_response = client.post(
        f"/api/v1/payments/{payment['id']}/confirm-mock",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "paid"

    order_response = client.get(
        f"/api/v1/orders/{order['id']}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert order_response.status_code == 200
    assert order_response.json()["status"] == "paid"


def test_invalid_payment_amount_is_rejected(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    buyer_token = _register_and_login(client, "buyer@example.com")
    order = _create_order(client, seller_token, buyer_token)

    response = client.post(
        "/api/v1/payments/intents",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={
            "order_id": order["id"],
            "amount": "100",
            "currency": "UZS",
            "provider": "mock",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Payment amount must match order final price"
