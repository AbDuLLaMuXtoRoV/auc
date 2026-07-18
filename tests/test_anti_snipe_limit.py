from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auction import Auction
from tests.conftest import AuthenticatedUser, create_auction, create_bid, create_item, create_user


def _setup_active_auction(
    client: TestClient,
    db_session: Session,
) -> tuple[int, AuthenticatedUser]:
    """Sotuvchi, lot va auksion yaratadi, bidder qaytaradi.

    Auksion boshlanishi o'tmishda, tugashi kelajakda — bid oqimi uni
    SCHEDULED -> ACTIVE ga o'tkazadi.
    """
    seller = create_user(client, db_session, email="seller@example.com")
    bidder = create_user(client, db_session, email="bidder@example.com")
    item = create_item(client, seller, starting_price="1000")
    auction = create_auction(
        client,
        seller,
        item["id"],
        minimum_bid_increment="100",
    )
    return auction["id"], bidder


def test_soft_close_extends_within_limit(client: TestClient, db_session: Session) -> None:
    """Limitgacha: oxirgi soniyadagi bid muddatni uzaytiradi, count oshadi."""
    auction_id, bidder = _setup_active_auction(client, db_session)

    # Tugashga oz qoldi (30s), hali bir marta ham uzaytirilmagan.
    auction = db_session.get(Auction, auction_id)
    assert auction is not None
    original_end_time = datetime.now(UTC) + timedelta(seconds=30)
    auction.end_time = original_end_time
    auction.extension_count = 0
    db_session.add(auction)
    db_session.commit()

    create_bid(client, bidder, auction_id, amount="1100")

    db_session.refresh(auction)
    # Muddat uzaydi, hisoblagich 1 ga oshdi.
    assert _as_utc(auction.end_time) > original_end_time
    assert auction.extension_count == 1


def test_soft_close_stops_at_limit(client: TestClient, db_session: Session) -> None:
    """Limitda: hisoblagich maksga yetgan bo'lsa bid muddatni SURMAYDI."""
    auction_id, bidder = _setup_active_auction(client, db_session)

    # Hisoblagich limitga yetgan, tugashga oz qoldi.
    auction = db_session.get(Auction, auction_id)
    assert auction is not None
    original_end_time = datetime.now(UTC) + timedelta(seconds=30)
    auction.end_time = original_end_time
    auction.extension_count = settings.max_soft_close_extensions
    db_session.add(auction)
    db_session.commit()

    create_bid(client, bidder, auction_id, amount="1100")

    db_session.refresh(auction)
    # Muddat o'zgarmadi, hisoblagich oshmadi — auksion o'z vaqtida yopiladi.
    assert _as_utc(auction.end_time) == original_end_time
    assert auction.extension_count == settings.max_soft_close_extensions


def _as_utc(value: datetime) -> datetime:
    """Postgres'dan naive qaytishi mumkin — taqqoslash uchun UTC'ga keltiradi."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
