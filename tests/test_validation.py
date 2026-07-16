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
        json={"condition": "used", "starting_price": "1000"},
    )
    assert missing_title_response.status_code == 422
    assert "title" in str(missing_title_response.json()["detail"])

    negative_price_response = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json={"title": "Invalid price", "condition": "used", "starting_price": "-100"},
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
            "minimum_bid_increment": "100",
        },
    )
    assert response.status_code == 422
    assert "Auction end time must be after start time" in str(response.json()["detail"])


def test_bid_rejects_fractional_tiyin_and_enforces_minimum_increment(
    client: TestClient,
    test_seller: AuthenticatedUser,
    test_user: AuthenticatedUser,
) -> None:
    """Pul birligi — tiyin. Undan maydasi yo'q, kasrli summa rad etiladi.

    Ilgari bu test Decimal aniqligini (decimal_places=2) tekshirardi.
    Endi pul butun tiyin: "1000.9" kabi kasrli qiymat umuman pul emas va
    422 bilan rad etilishi kerak — jimgina yaxlitlanmasligi shart.
    Minimal qadam tekshiruvi esa o'z kuchida qoladi.
    """
    # 10.00 so'm = 1000 tiyin, minimal qadam 0.01 so'm = 1 tiyin.
    item = create_item(client, test_seller, starting_price="1000")
    auction = create_auction(
        client,
        test_seller,
        item["id"],
        minimum_bid_increment="1",
    )

    fractional_response = client.post(
        f"/api/v1/bids/{auction['id']}",
        headers=test_user.headers,
        json={"amount": "1000.9"},
    )
    assert fractional_response.status_code == 422

    # Minimal qadamdan past bid — boshlang'ich narxga teng, qadam qo'shilmagan.
    too_low_response = client.post(
        f"/api/v1/bids/{auction['id']}",
        headers=test_user.headers,
        json={"amount": "1000"},
    )
    assert too_low_response.status_code == 400

    bid = create_bid(client, test_user, auction["id"], amount="1001")
    assert bid["amount"] == "1001"
