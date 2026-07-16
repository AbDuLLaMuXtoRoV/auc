from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.auction import Auction


def _register_and_login(client: TestClient, email: str) -> str:
    password = "Password1"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _create_auction(
    client: TestClient,
    seller_token: str,
    *,
    status: str | None = None,
    start_delta: timedelta = -timedelta(minutes=1),
    end_delta: timedelta = timedelta(days=1),
) -> int:
    item_response = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "title": "Socket set",
            "condition": "used",
            "starting_price": "2000",
        },
    )
    assert item_response.status_code == 201

    now = datetime.now(UTC)
    auction_response = client.post(
        "/api/v1/auctions",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "item_id": item_response.json()["id"],
            "start_time": (now + start_delta).isoformat(),
            "end_time": (now + end_delta).isoformat(),
            "minimum_bid_increment": "500",
        },
    )
    assert auction_response.status_code == 201
    auction_id = auction_response.json()["id"]

    if status is not None:
        status_response = client.patch(
            f"/api/v1/auctions/{auction_id}/status",
            headers={"Authorization": f"Bearer {seller_token}"},
            json={"status": status},
        )
        assert status_response.status_code == 200

    return auction_id


def test_bid_rules(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    bidder_token = _register_and_login(client, "bidder@example.com")
    auction_id = _create_auction(client, seller_token)

    own_bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"amount": "2500"},
    )
    assert own_bid_response.status_code == 400

    low_bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "2100"},
    )
    assert low_bid_response.status_code == 400

    valid_bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "2500"},
    )
    assert valid_bid_response.status_code == 201
    assert valid_bid_response.json()["amount"] == "2500"

    auction_response = client.get(f"/api/v1/auctions/{auction_id}")
    assert auction_response.status_code == 200
    auction = auction_response.json()
    assert auction["current_price"] == "2500"
    assert auction["highest_bidder_id"] == valid_bid_response.json()["bidder_id"]
    assert auction["winning_bid_id"] == valid_bid_response.json()["id"]

    second_low_bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "2900"},
    )
    assert second_low_bid_response.status_code == 400

    repeat_bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "3000"},
    )
    assert repeat_bid_response.status_code == 201

    updated_auction_response = client.get(f"/api/v1/auctions/{auction_id}")
    assert updated_auction_response.status_code == 200
    updated_auction = updated_auction_response.json()
    assert updated_auction["current_price"] == "3000"
    assert updated_auction["highest_bidder_id"] == repeat_bid_response.json()["bidder_id"]


def test_bid_rejected_when_auction_is_not_active(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    bidder_token = _register_and_login(client, "bidder@example.com")
    auction_id = _create_auction(client, seller_token, status="cancelled")

    response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "2500"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Auction is not active"


def test_bid_rejected_when_auction_has_ended(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    bidder_token = _register_and_login(client, "bidder@example.com")
    auction_id = _create_auction(
        client,
        seller_token,
        start_delta=-timedelta(days=2),
        end_delta=-timedelta(days=1),
    )

    response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "2500"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Auction has ended"


def test_scheduled_auction_activates_when_bid_is_placed_after_start_time(
    client: TestClient,
    db_session: Session,
) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    bidder_token = _register_and_login(client, "bidder@example.com")
    auction_id = _create_auction(
        client,
        seller_token,
        start_delta=timedelta(days=1),
        end_delta=timedelta(days=2),
    )

    scheduled_response = client.get(f"/api/v1/auctions/{auction_id}")
    assert scheduled_response.status_code == 200
    assert scheduled_response.json()["status"] == "scheduled"

    auction = db_session.get(Auction, auction_id)
    assert auction is not None
    auction.start_time = datetime.now(UTC) - timedelta(minutes=1)
    auction.end_time = datetime.now(UTC) + timedelta(days=1)
    db_session.add(auction)
    db_session.commit()

    bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "2500"},
    )
    assert bid_response.status_code == 201

    active_response = client.get(f"/api/v1/auctions/{auction_id}")
    assert active_response.status_code == 200
    assert active_response.json()["status"] == "active"


def test_anti_sniping_extends_auction_end_time(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    bidder_token = _register_and_login(client, "bidder@example.com")
    auction_id = _create_auction(
        client,
        seller_token,
        start_delta=-timedelta(minutes=1),
        end_delta=timedelta(seconds=90),
    )
    before_bid_response = client.get(f"/api/v1/auctions/{auction_id}")
    assert before_bid_response.status_code == 200
    original_end_time = datetime.fromisoformat(before_bid_response.json()["end_time"])

    bid_response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers={"Authorization": f"Bearer {bidder_token}"},
        json={"amount": "2500"},
    )
    assert bid_response.status_code == 201

    after_bid_response = client.get(f"/api/v1/auctions/{auction_id}")
    assert after_bid_response.status_code == 200
    extended_end_time = datetime.fromisoformat(after_bid_response.json()["end_time"])
    assert extended_end_time > original_end_time
