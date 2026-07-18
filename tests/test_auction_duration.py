"""Auksion muddatini duration_days (3/5/7 kun) orqali berish testlari.

Mahsulotning asosiy qoidasi — majburiy deadline. duration_days end_time'ga
MUQOBIL yo'l: berilsa end_time = start_time + kun sifatida hisoblanadi.
Eski end_time yo'li o'zgarmaydi (orqaga moslik).
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.conftest import AuthenticatedUser, create_item


def _create_auction_raw(
    client: TestClient,
    seller: AuthenticatedUser,
    item_id: int,
    *,
    payload_extra: dict,
) -> "object":
    """Auksionni to'g'ridan-to'g'ri POST qiladi (conftest helperi end_time majbur qiladi)."""
    now = datetime.now(UTC)
    payload = {
        "item_id": item_id,
        "start_time": now.isoformat(),
        "minimum_bid_increment": "100",
        **payload_extra,
    }
    return client.post("/api/v1/auctions", headers=seller.headers, json=payload)


def test_create_with_duration_days(client: TestClient, test_seller: AuthenticatedUser) -> None:
    """duration_days=5 (end_time'siz) → 201, end_time ≈ start+5kun, duration saqlangan."""
    item = create_item(client, test_seller)
    response = _create_auction_raw(
        client, test_seller, item["id"], payload_extra={"duration_days": 5}
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["duration_days"] == 5
    start = datetime.fromisoformat(body["start_time"])
    end = datetime.fromisoformat(body["end_time"])
    # end_time = start_time + 5 kun (soniya aniqligida).
    assert abs((end - start) - timedelta(days=5)) < timedelta(seconds=1)


def test_invalid_duration_days_rejected(client: TestClient, test_seller: AuthenticatedUser) -> None:
    """duration_days=4 (3/5/7 dan emas) → 422."""
    item = create_item(client, test_seller)
    response = _create_auction_raw(
        client, test_seller, item["id"], payload_extra={"duration_days": 4}
    )
    assert response.status_code == 422, response.text


def test_neither_end_time_nor_duration(client: TestClient, test_seller: AuthenticatedUser) -> None:
    """Na end_time na duration_days → 422."""
    item = create_item(client, test_seller)
    response = _create_auction_raw(client, test_seller, item["id"], payload_extra={})
    assert response.status_code == 422, response.text


def test_both_end_time_and_duration(client: TestClient, test_seller: AuthenticatedUser) -> None:
    """end_time va duration_days ikkalasi ham berilsa → 422 (aynan bittasi)."""
    item = create_item(client, test_seller)
    end_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    response = _create_auction_raw(
        client,
        test_seller,
        item["id"],
        payload_extra={"end_time": end_time, "duration_days": 3},
    )
    assert response.status_code == 422, response.text


def test_end_time_only_backward_compatible(
    client: TestClient, test_seller: AuthenticatedUser
) -> None:
    """Faqat end_time (eski yo'l) → 201, duration_days null (orqaga moslik)."""
    item = create_item(client, test_seller)
    end_time = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    response = _create_auction_raw(
        client, test_seller, item["id"], payload_extra={"end_time": end_time}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["duration_days"] is None
