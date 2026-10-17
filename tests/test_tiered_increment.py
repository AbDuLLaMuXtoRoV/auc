"""Dinamik (darajali) minimal qadam jadvali testlari.

Barcha qiymatlar TIYINDA. Jadval chegaralari EKSKLYUZIV: narx aynan chegaraga
teng bo'lsa keyingi (kattaroq qadamli) darajaga o'tadi.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.services.bid_increment import effective_min_increment, min_increment_for_price
from tests.conftest import create_auction, create_item, create_user


def test_min_increment_tier_boundaries() -> None:
    # < 100 000 so'm (< 10 000 000 tiyin) -> 5 000 so'm (500 000 tiyin)
    assert min_increment_for_price(0) == 500_000
    assert min_increment_for_price(9_999_999) == 500_000
    # 100 000..500 000 so'm -> 10 000 so'm (1 000 000 tiyin)
    assert min_increment_for_price(10_000_000) == 1_000_000
    assert min_increment_for_price(49_999_999) == 1_000_000
    # 500 000..2 000 000 so'm -> 25 000 so'm (2 500 000 tiyin)
    assert min_increment_for_price(50_000_000) == 2_500_000
    assert min_increment_for_price(199_999_999) == 2_500_000
    # 2 000 000..10 000 000 so'm -> 100 000 so'm (10 000 000 tiyin)
    assert min_increment_for_price(200_000_000) == 10_000_000
    assert min_increment_for_price(999_999_999) == 10_000_000
    # > 10 000 000 so'm -> 250 000 so'm (25 000 000 tiyin)
    assert min_increment_for_price(1_000_000_000) == 25_000_000
    assert min_increment_for_price(5_000_000_000) == 25_000_000


def test_effective_increment_takes_higher_of_seller_or_tier() -> None:
    # Sotuvchi qadami jadvaldan PAST — jadval qadami g'olib (majburiy pol).
    assert effective_min_increment(5_000_000, 100) == 500_000
    # Sotuvchi qadami jadvaldan YUQORI — sotuvchi qadami g'olib.
    assert effective_min_increment(5_000_000, 1_000_000) == 1_000_000
    # Teng bo'lsa — o'sha qiymat.
    assert effective_min_increment(5_000_000, 500_000) == 500_000


def test_bid_must_meet_tiered_increment_even_with_tiny_seller_step(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    """Sotuvchi kichik qadam qo'ysa ham, jadval qadami majburiy pol bo'lib qoladi."""
    # conftest jadvalni test muhitida o'chiradi — bu test uni ataylab yoqadi
    # (bid_service pol majburiyligini haqiqiy oqim orqali tekshirish uchun).
    from app.core.config import settings

    monkeypatch.setattr(settings, "tiered_bid_increment_enabled", True)
    seller = create_user(client, db_session, email="seller@example.com", role=UserRole.SELLER)
    bidder = create_user(client, db_session, email="bidder@example.com")
    item = create_item(client, seller, starting_price="5000000")
    auction = create_auction(client, seller, item["id"], minimum_bid_increment="100")

    # 5 000 100 = joriy + sotuvchi qadami (100), lekin jadval qadami 500 000.
    too_low = client.post(
        f"/api/v1/bids/{auction['id']}",
        headers=bidder.headers,
        json={"amount": "5000100"},
    )
    assert too_low.status_code == 400

    ok = client.post(
        f"/api/v1/bids/{auction['id']}",
        headers=bidder.headers,
        json={"amount": "5500000"},
    )
    assert ok.status_code == 201
