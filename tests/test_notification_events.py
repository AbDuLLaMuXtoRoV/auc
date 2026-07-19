"""Event integratsiyasi: bid/close bildirishnoma chiqaradi.

Bu subsystemlarni ulaydi — bid_service OUTBID, auction_service WON/SOLD.
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
    return login.json()["access_token"]


def _create_active_auction(client: TestClient, seller: str) -> int:
    item = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller}"},
        json={"title": "Console", "condition": "used", "starting_price": "100000"},
    )
    now = datetime.now(UTC)
    auction = client.post(
        "/api/v1/auctions",
        headers={"Authorization": f"Bearer {seller}"},
        json={
            "item_id": item.json()["id"],
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "minimum_bid_increment": "10000",
        },
    )
    return auction.json()["id"]


def _types(client: TestClient, token: str) -> set[str]:
    r = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    return {n["type"] for n in r.json()}


def test_outbid_notification(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    a = _register_and_login(client, "a@example.com")
    b = _register_and_login(client, "b@example.com")
    auction_id = _create_active_auction(client, seller)

    # A leader bo'ladi (max'siz oddiy bid).
    client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {a}"},
        json={"amount": "110000"},
    )
    # B A'ni ortda qoldiradi.
    client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {b}"},
        json={"amount": "120000"},
    )

    assert "outbid" in _types(client, a)  # A xabar oldi
    assert "outbid" not in _types(client, b)  # B leader, ortda qolmadi


def test_won_and_sold_notifications(client: TestClient) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    auction_id = _create_active_auction(client, seller)

    client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"amount": "110000"},
    )
    close = client.post(
        f"/api/v1/auctions/{auction_id}/close",
        headers={"Authorization": f"Bearer {seller}"},
    )
    assert close.status_code == 200

    assert "won" in _types(client, buyer)
    assert "sold" in _types(client, seller)
