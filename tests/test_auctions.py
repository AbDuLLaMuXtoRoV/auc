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


def test_create_and_close_auction(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    bidder_token = _register_and_login(client, "bidder@example.com")

    item_response = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "title": "Cordless drill",
            "description": "Lightly used drill with charger",
            "condition": "used",
            "images": ["https://example.com/drill.jpg"],
            "location": "Tashkent",
            "item_location": "Tashkent warehouse",
            "starting_price": "5000",
            "reserve_price": "5500",
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
            "minimum_bid_increment": "500",
        },
    )
    assert auction_response.status_code == 201
    auction = auction_response.json()

    bid_response = client.post(
        f"/api/v1/auctions/{auction['id']}/bids",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "6000"},
    )
    assert bid_response.status_code == 201

    close_response = client.post(
        f"/api/v1/auctions/{auction['id']}/close",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert close_response.status_code == 200
    assert close_response.json()["winner_id"] is not None
    assert close_response.json()["status"] == "ended"


def test_close_auction_marks_reserve_not_met(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    bidder_token = _register_and_login(client, "bidder@example.com")

    item_response = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "title": "Vintage turntable",
            "condition": "used",
            "starting_price": "5000",
            "reserve_price": "10000",
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
            "minimum_bid_increment": "500",
        },
    )
    assert auction_response.status_code == 201
    auction = auction_response.json()

    bid_response = client.post(
        f"/api/v1/auctions/{auction['id']}/bids",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "6000"},
    )
    assert bid_response.status_code == 201

    close_response = client.post(
        f"/api/v1/auctions/{auction['id']}/close",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert close_response.status_code == 200
    assert close_response.json()["winner_id"] == bid_response.json()["bidder_id"]
    assert close_response.json()["status"] == "reserve_not_met"


def test_auction_can_only_be_created_for_draft_or_scheduled_item(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    item_response = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "title": "Already active item",
            "condition": "used",
            "starting_price": "2500",
        },
    )
    assert item_response.status_code == 201
    item_id = item_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"status": "active"},
    )
    assert update_response.status_code == 200

    now = datetime.now(UTC)
    auction_response = client.post(
        "/api/v1/auctions",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "item_id": item_id,
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "minimum_bid_increment": "500",
        },
    )
    assert auction_response.status_code == 400
    assert auction_response.json()["detail"] == (
        "Auction can only be created for a draft or scheduled item"
    )
