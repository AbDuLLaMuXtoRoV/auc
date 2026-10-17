"""Bid retraction (foydalanuvchi) va invalidation (admin) testlari.

Realistik narxlar ishlatiladi — dinamik minimal qadam jadvali kuchga kirgani
uchun kichik summalar (masalan 1000 tiyin) endi validatsiyadan o'tmaydi.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.auction import Auction
from app.models.enums import UserRole
from tests.conftest import create_auction, create_item, create_user


def _setup(client: TestClient, db_session: Session):
    seller = create_user(client, db_session, email="seller@example.com", role=UserRole.SELLER)
    bidder_a = create_user(client, db_session, email="a@example.com")
    bidder_b = create_user(client, db_session, email="b@example.com")
    item = create_item(client, seller, starting_price="5000000")
    auction = create_auction(client, seller, item["id"], minimum_bid_increment="100")
    return seller, bidder_a, bidder_b, auction


def _bid(client: TestClient, user, auction_id: int, amount: int) -> dict:
    response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers=user.headers,
        json={"amount": str(amount)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_non_leader_can_retract_price_holds(client: TestClient, db_session: Session) -> None:
    seller, bidder_a, bidder_b, auction = _setup(client, db_session)
    bid_a = _bid(client, bidder_a, auction["id"], 6_000_000)
    _bid(client, bidder_b, auction["id"], 7_000_000)  # B yetakchi, A outbid

    resp = client.post(f"/api/v1/bids/{bid_a['id']}/retract", headers=bidder_a.headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "retracted"

    state = client.get(f"/api/v1/auctions/{auction['id']}").json()
    # Yetakchi bo'lmagan bid qaytarilsa — narx va yetakchi o'zgarmaydi.
    assert state["current_price"] == "7000000"
    assert state["highest_bidder_id"] == bidder_b.id


def test_leader_cannot_retract(client: TestClient, db_session: Session) -> None:
    seller, bidder_a, bidder_b, auction = _setup(client, db_session)
    _bid(client, bidder_a, auction["id"], 6_000_000)
    bid_b = _bid(client, bidder_b, auction["id"], 7_000_000)  # B yetakchi

    resp = client.post(f"/api/v1/bids/{bid_b['id']}/retract", headers=bidder_b.headers)
    assert resp.status_code == 409


def test_cannot_retract_someone_elses_bid(client: TestClient, db_session: Session) -> None:
    seller, bidder_a, bidder_b, auction = _setup(client, db_session)
    bid_a = _bid(client, bidder_a, auction["id"], 6_000_000)
    _bid(client, bidder_b, auction["id"], 7_000_000)

    resp = client.post(f"/api/v1/bids/{bid_a['id']}/retract", headers=bidder_b.headers)
    assert resp.status_code == 403


def test_cannot_retract_near_close(client: TestClient, db_session: Session) -> None:
    seller, bidder_a, bidder_b, auction = _setup(client, db_session)
    bid_a = _bid(client, bidder_a, auction["id"], 6_000_000)
    _bid(client, bidder_b, auction["id"], 7_000_000)  # A yetakchi emas

    # Tugashni soft-close oynasi ichiga suramiz.
    db_session.expire_all()
    row = db_session.get(Auction, auction["id"])
    assert row is not None
    row.end_time = datetime.now(UTC) + timedelta(seconds=30)
    db_session.add(row)
    db_session.commit()

    resp = client.post(f"/api/v1/bids/{bid_a['id']}/retract", headers=bidder_a.headers)
    assert resp.status_code == 409


def test_admin_invalidate_recomputes_price(client: TestClient, db_session: Session) -> None:
    seller, bidder_a, bidder_b, auction = _setup(client, db_session)
    _bid(client, bidder_a, auction["id"], 6_000_000)
    bid_b = _bid(client, bidder_b, auction["id"], 7_000_000)  # B yetakchi, A outbid
    admin = create_user(client, db_session, email="admin@example.com", role=UserRole.ADMIN)

    resp = client.post(
        f"/api/v1/bids/{bid_b['id']}/invalidate",
        headers=admin.headers,
        json={"reason": "shill halqasi"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "invalidated"

    state = client.get(f"/api/v1/auctions/{auction['id']}").json()
    # Yetakchi bid bekor qilingach, A ning bidi qayta tiklanib narx 6M ga tushadi.
    assert state["current_price"] == "6000000"
    assert state["highest_bidder_id"] == bidder_a.id


def test_non_admin_cannot_invalidate(client: TestClient, db_session: Session) -> None:
    seller, bidder_a, bidder_b, auction = _setup(client, db_session)
    _bid(client, bidder_a, auction["id"], 6_000_000)
    bid_b = _bid(client, bidder_b, auction["id"], 7_000_000)

    resp = client.post(
        f"/api/v1/bids/{bid_b['id']}/invalidate",
        headers=bidder_b.headers,
        json={"reason": "o'zimni yutqazyapman"},
    )
    assert resp.status_code == 403


def test_denormalized_counts_track_bids(client: TestClient, db_session: Session) -> None:
    seller, bidder_a, bidder_b, auction = _setup(client, db_session)
    _bid(client, bidder_a, auction["id"], 6_000_000)
    _bid(client, bidder_b, auction["id"], 7_000_000)

    state = client.get(f"/api/v1/auctions/{auction['id']}").json()
    assert state["bid_count"] == 2
    assert state["unique_bidder_count"] == 2
