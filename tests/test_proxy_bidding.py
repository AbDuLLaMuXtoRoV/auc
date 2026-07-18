"""Proxy bidding (max-bid) testlari.

Semantика (orqaga mos):
  - max_amount berilmasa — oddiy bid, ko'ringan narx = amount.
  - max_amount berilsa — tizim leader nomidan keyingi raqiblarга qarshi
    avtomatik bir qadam yuqoriga ko'taradi (leader max'igacha).

KRITIK: high_bidder_max / max_amount HECH QACHON API javobida oshkor
bo'lmaydi.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.auction import Auction


def _register_and_login(client: TestClient, email: str) -> tuple[str, int]:
    password = "Password1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert reg.status_code == 201
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"], reg.json()["id"]


def _create_auction(client: TestClient, seller_token: str) -> int:
    headers = {"Authorization": f"Bearer {seller_token}"}
    item = client.post(
        "/api/v1/items",
        headers=headers,
        json={"title": "Camera", "condition": "used", "starting_price": "100000"},
    )
    assert item.status_code == 201
    now = datetime.now(UTC)
    auction = client.post(
        "/api/v1/auctions",
        headers=headers,
        json={
            "item_id": item.json()["id"],
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "minimum_bid_increment": "5000",
        },
    )
    assert auction.status_code == 201
    return auction.json()["id"]


def _bid(
    client: TestClient, token: str, auction_id: int, amount: str, max_amount: str | None = None
):
    body: dict[str, str] = {"amount": amount}
    if max_amount is not None:
        body["max_amount"] = max_amount
    return client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )


def test_proxy_defends_leader_automatically(client: TestClient) -> None:
    """Doc namunasi: A max=200k, B 150k -> A yutadi, narx 155k.

    start=100k, step=5k. A ko'ringan bid 105k + max 200k. B ko'ringan bid 150k.
    Leader A max'i 200k >= 150k+5k => A avtomatik 155k gacha ko'tariladi.
    """
    seller_token, _ = _register_and_login(client, "seller@example.com")
    a_token, a_id = _register_and_login(client, "a@example.com")
    b_token, b_id = _register_and_login(client, "b@example.com")
    auction_id = _create_auction(client, seller_token)

    assert _bid(client, a_token, auction_id, "105000", max_amount="200000").status_code == 201
    assert _bid(client, b_token, auction_id, "150000").status_code == 201

    auction = client.get(f"/api/v1/auctions/{auction_id}").json()
    # Proxy himoyasi: narx B'ning 150k'idan bir qadam yuqori, A hali leader.
    assert auction["current_price"] == "155000"
    assert auction["highest_bidder_id"] == a_id
    assert auction["highest_bidder_id"] != b_id


def test_proxy_secret_never_leaks(client: TestClient) -> None:
    """high_bidder_max / max_amount API javoblarida bo'lmasligi shart."""
    seller_token, _ = _register_and_login(client, "seller@example.com")
    a_token, _ = _register_and_login(client, "a@example.com")
    auction_id = _create_auction(client, seller_token)

    _bid(client, a_token, auction_id, "105000", max_amount="500000")

    auction = client.get(f"/api/v1/auctions/{auction_id}").json()
    assert "high_bidder_max" not in auction

    bids = client.get(f"/api/v1/auctions/{auction_id}/bids")
    if bids.status_code == 200:
        for bid in bids.json():
            assert "max_amount" not in bid


def test_challenger_beats_leader_max(client: TestClient) -> None:
    """Raqib leader max'idan oshib ketsa — o'zi leader bo'ladi (o'z narxida)."""
    seller_token, _ = _register_and_login(client, "seller@example.com")
    a_token, _ = _register_and_login(client, "a@example.com")
    b_token, b_id = _register_and_login(client, "b@example.com")
    auction_id = _create_auction(client, seller_token)

    _bid(client, a_token, auction_id, "105000", max_amount="150000")
    # B ko'ringan bidi 160k > A max 150k => B leader, narx 160k.
    assert _bid(client, b_token, auction_id, "160000", max_amount="160000").status_code == 201

    auction = client.get(f"/api/v1/auctions/{auction_id}").json()
    assert auction["current_price"] == "160000"
    assert auction["highest_bidder_id"] == b_id


def test_simple_bid_without_max_unchanged(client: TestClient, db_session: Session) -> None:
    """max_amount'siz bid — eski xatti-harakat: narx = amount, proxy o'chiq."""
    seller_token, _ = _register_and_login(client, "seller@example.com")
    a_token, _ = _register_and_login(client, "a@example.com")
    auction_id = _create_auction(client, seller_token)

    assert _bid(client, a_token, auction_id, "105000").status_code == 201

    auction = client.get(f"/api/v1/auctions/{auction_id}").json()
    assert auction["current_price"] == "105000"

    # max_amount berilmagani sababli high_bidder_max = amount bo'ldi (yashirin).
    row = db_session.get(Auction, auction_id)
    assert row.high_bidder_max == 105000


def test_max_below_amount_rejected(client: TestClient) -> None:
    """max_amount < amount — 422 (Pydantic validatsiya)."""
    seller_token, _ = _register_and_login(client, "seller@example.com")
    a_token, _ = _register_and_login(client, "a@example.com")
    auction_id = _create_auction(client, seller_token)

    r = _bid(client, a_token, auction_id, "105000", max_amount="100000")
    assert r.status_code == 422
