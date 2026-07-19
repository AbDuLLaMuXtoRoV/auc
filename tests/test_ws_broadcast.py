"""WS avto-broadcast: real bid -> kuzatuvchilarga BID_PLACED.

Sync bid oqimi (threadpool) -> manager.broadcast_threadsafe -> app event
loop -> WS mijozlariga. high_bidder_max/max_amount HECH QACHON yuborilmaydi.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.realtime.manager import ConnectionManager


def _login(client: TestClient, email: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password1", "full_name": email.split("@")[0]},
    )
    r = client.post("/api/v1/auth/login", data={"username": email, "password": "Password1"})
    return r.json()["access_token"]


def test_broadcast_threadsafe_without_loop_is_noop() -> None:
    """Loop o'rnatilmagan bo'lsa broadcast_threadsafe xato bermaydi (best-effort)."""
    m = ConnectionManager()
    # Hech qanday loop yo'q — jimgina o'tkazib yuboradi.
    m.broadcast_threadsafe(1, {"type": "X"})


def test_bid_broadcasts_to_ws_watchers(client: TestClient) -> None:
    seller = _login(client, "seller@example.com")
    bidder = _login(client, "bidder@example.com")
    watcher = _login(client, "watcher@example.com")

    item = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller}"},
        json={"title": "Watch me", "condition": "used", "starting_price": "100000"},
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
    auction_id = auction.json()["id"]

    with client.websocket_connect(f"/api/v1/ws/auctions/{auction_id}?token={watcher}") as ws:
        bid = client.post(
            f"/api/v1/bids/{auction_id}",
            headers={"Authorization": f"Bearer {bidder}"},
            json={"amount": "110000"},
        )
        assert bid.status_code == 201

        message = ws.receive_json()
        assert message["type"] == "BID_PLACED"
        assert message["auction_id"] == auction_id
        assert message["current_price"] == "110000"
        # Maxfiylik: proxy siri hech qachon yuborilmaydi.
        assert "high_bidder_max" not in message
        assert "max_amount" not in message
