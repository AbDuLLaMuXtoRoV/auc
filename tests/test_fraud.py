"""Anti-fraud signal servisi va admin endpointi testlari.

Bid yozuvlari TO'G'RIDAN-TO'G'RI `db_session` orqali seed qilinadi — endpoint
orqali emas: TestClient IP'ni "testclient" beradi (INET emas) va `bid.ip`
None bo'lib qolardi, natijada IP signallari sinovdan o'tmasdi. Shu sababli
signal ssenariylari FraudService'ni to'g'ridan-to'g'ri chaqiradi; endpoint
faqat ruxsat (403) uchun HTTP orqali sinaladi.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.auction import Auction
from app.models.bid import Bid
from app.models.enums import AuctionStatus, ItemCondition, ItemStatus, UserRole
from app.models.item import Item
from app.models.user import User
from app.services.fraud_service import FraudService


def _make_user(db: Session, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        email=email,
        hashed_password="x",
        full_name=email.split("@")[0],
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def _make_auction(db: Session, seller: User) -> Auction:
    item = Item(
        seller_id=seller.id,
        title="Lot",
        condition=ItemCondition.USED,
        status=ItemStatus.ACTIVE,
        starting_price=1000,
    )
    db.add(item)
    db.flush()
    now = datetime.now(UTC)
    auction = Auction(
        item_id=item.id,
        seller_id=seller.id,
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(days=1),
        starting_price=1000,
        current_price=1000,
        status=AuctionStatus.ACTIVE,
    )
    db.add(auction)
    db.flush()
    return auction


def _make_bid(
    db: Session,
    auction: Auction,
    bidder: User,
    *,
    ip: str | None = None,
    device_id: str | None = None,
    amount: int = 1100,
    created_at: datetime | None = None,
) -> Bid:
    bid = Bid(
        auction_id=auction.id,
        bidder_id=bidder.id,
        amount=amount,
        max_amount=amount,
        ip=ip,
        device_id=device_id,
    )
    if created_at is not None:
        bid.created_at = created_at
    db.add(bid)
    db.flush()
    return bid


def test_shared_device_detected(db_session: Session) -> None:
    """Ikki akkaunt bir device_id dan bid qo'ysa, bir-birini topadi."""
    seller = _make_user(db_session, "seller@example.com", UserRole.SELLER)
    u1 = _make_user(db_session, "u1@example.com")
    u2 = _make_user(db_session, "u2@example.com")
    auction = _make_auction(db_session, seller)

    _make_bid(db_session, auction, u1, device_id="dev-x", ip="10.0.0.1")
    _make_bid(db_session, auction, u2, device_id="dev-x", ip="10.0.0.2")

    signals = FraudService(db_session).signals_for_user(u1.id)

    assert signals["shared_device_user_ids"] == [u2.id]
    assert "shared_device" in signals["risk_flags"]
    # IP har xil — shared_ip bayrog'i ko'tarilmaydi.
    assert signals["shared_ip_user_ids"] == []
    assert "shared_ip" not in signals["risk_flags"]


def test_shill_ip_overlap_detected(db_session: Session) -> None:
    """Bidder auksion sotuvchisi bilan bir IP ishlatsa (alt-akkaunt shill).

    Sotuvchi o'z lotiga bid qo'yolmaydi, shuning uchun uning IP izi boshqa
    auksiondagi bididan olinadi (bu yerda A2).
    """
    seller = _make_user(db_session, "shill-seller@example.com", UserRole.SELLER)
    other_seller = _make_user(db_session, "other-seller@example.com", UserRole.SELLER)
    bidder = _make_user(db_session, "bidder@example.com")

    auction_a1 = _make_auction(db_session, seller)  # bidder shu yerda bid qo'yadi
    auction_a2 = _make_auction(db_session, other_seller)  # seller boshqa joyda bid qo'yadi

    shared_ip = "77.88.99.100"
    _make_bid(db_session, auction_a1, bidder, ip=shared_ip)
    _make_bid(db_session, auction_a2, seller, ip=shared_ip)

    signals = FraudService(db_session).signals_for_user(bidder.id)

    assert signals["self_auction_ip_overlap"] > 0
    assert "shill_ip_overlap" in signals["risk_flags"]


def test_clean_user_has_no_flags(db_session: Session) -> None:
    """Alohida ip/device ishlatgan toza foydalanuvchi — bayroqlar bo'sh."""
    seller = _make_user(db_session, "seller2@example.com", UserRole.SELLER)
    clean = _make_user(db_session, "clean@example.com")
    auction = _make_auction(db_session, seller)

    _make_bid(db_session, auction, clean, ip="5.5.5.5", device_id="dev-clean")

    signals = FraudService(db_session).signals_for_user(clean.id)

    assert signals["shared_device_user_ids"] == []
    assert signals["shared_ip_user_ids"] == []
    assert signals["self_auction_ip_overlap"] == 0
    assert signals["bid_count"] == 1
    assert signals["distinct_auctions"] == 1
    assert signals["risk_flags"] == []


def test_high_velocity_detected(db_session: Session) -> None:
    """10 soniyada 3+ bid — high_velocity bayrog'i."""
    seller = _make_user(db_session, "seller3@example.com", UserRole.SELLER)
    bot = _make_user(db_session, "bot@example.com")
    auction = _make_auction(db_session, seller)

    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    for offset in (0, 2, 4, 6):  # 4 ta bid 6 soniya ichida
        _make_bid(
            db_session, auction, bot, ip="8.8.8.8", created_at=base + timedelta(seconds=offset)
        )

    signals = FraudService(db_session).signals_for_user(bot.id)

    assert signals["rapid_bid_max_per_10s"] >= 3
    assert "high_velocity" in signals["risk_flags"]


def test_endpoint_requires_admin(client: TestClient, test_user) -> None:
    """Admin bo'lmagan foydalanuvchi 403 oladi (signal hisoblanmaydi)."""
    response = client.get(
        f"/api/v1/fraud/signals/{test_user.id}",
        headers=test_user.headers,
    )
    assert response.status_code == 403


def test_endpoint_admin_ok(client: TestClient, db_session: Session, test_admin) -> None:
    """Admin 200 oladi va signal shakli to'g'ri qaytadi."""
    seller = _make_user(db_session, "seller4@example.com", UserRole.SELLER)
    target = _make_user(db_session, "target@example.com")
    auction = _make_auction(db_session, seller)
    _make_bid(db_session, auction, target, ip="1.2.3.4", device_id="dev-a")
    db_session.commit()

    response = client.get(
        f"/api/v1/fraud/signals/{target.id}",
        headers=test_admin.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == target.id
    assert body["bid_count"] == 1
    assert body["distinct_auctions"] == 1
    assert isinstance(body["risk_flags"], list)
