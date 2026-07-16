from datetime import UTC, datetime, timedelta

from conftest import AuthenticatedUser, create_auction, create_bid, create_item
from fastapi.testclient import TestClient


def test_email_and_password_validation(client: TestClient) -> None:
    invalid_email_response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "Password1"},
    )
    assert invalid_email_response.status_code == 422

    weak_password_response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "password"},
    )
    assert weak_password_response.status_code == 422


def test_item_required_fields_and_price_validation(
    client: TestClient,
    test_seller: AuthenticatedUser,
) -> None:
    missing_title_response = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json={"condition": "used", "starting_price": "10.00"},
    )
    assert missing_title_response.status_code == 422
    assert "title" in str(missing_title_response.json()["detail"])

    negative_price_response = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json={"title": "Invalid price", "condition": "used", "starting_price": "-1.00"},
    )
    assert negative_price_response.status_code == 422


def test_auction_time_validation(
    client: TestClient,
    test_seller: AuthenticatedUser,
) -> None:
    item = create_item(client, test_seller)
    now = datetime.now(UTC)
    response = client.post(
        "/api/v1/auctions",
        headers=test_seller.headers,
        json={
            "item_id": item["id"],
            "start_time": now.isoformat(),
            "end_time": (now - timedelta(minutes=1)).isoformat(),
            "minimum_bid_increment": "1.00",
        },
    )
    assert response.status_code == 422
    assert "Auction end time must be after start time" in str(response.json()["detail"])


def test_bid_decimal_precision_and_minimum_increment(
    client: TestClient,
    test_seller: AuthenticatedUser,
    test_user: AuthenticatedUser,
) -> None:
    item = create_item(client, test_seller, starting_price="10.00")
    auction = create_auction(
        client,
        test_seller,
        item["id"],
        minimum_bid_increment="0.01",
    )

    too_precise_response = client.post(
        f"/api/v1/bids/{auction['id']}",
        headers=test_user.headers,
        json={"amount": "10.009"},
    )
    assert too_precise_response.status_code == 422

    bid = create_bid(client, test_user, auction["id"], amount="10.01")
    assert bid["amount"] == "10.01"
