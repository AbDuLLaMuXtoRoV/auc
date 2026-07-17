"""Race condition testi: parallel bidlarda faqat bittasi yutadi.

NEGA ALOHIDA FAYL: qolgan testlar bitta ulashilgan sessiya (bitta ulanish)
orqali ketma-ket ishlaydi — ular haqiqiy parallellikni SINAB KO'RA OLMAYDI.
`FOR UPDATE` qulfini isbotlash uchun har thread'da ALOHIDA DB ulanishi
kerak, aks holda hech qanday raqobat yuzaga kelmaydi.

Bu test qulf regressiyasini tutadi: agar `get_for_update` oddiy `get` ga
qaytarilsa (yoki commit qulfni erta bo'shatsa), bir nechta bid bir xil
`current_price` ni o'qib, hammasi validatsiyadan o'tadi va lost update
yuz beradi — test yiqiladi.
"""

import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.models.auction import Auction
from app.models.bid import Bid
from app.models.enums import AuctionStatus, BidStatus, ItemCondition, ItemStatus, UserRole
from app.models.item import Item
from app.models.user import User
from app.schemas.bid import BidCreate
from app.services.bid_service import BidService
from tests.conftest import TEST_PASSWORD

CONCURRENCY = 12
STARTING_PRICE = 100_000  # tiyin
INCREMENT = 10_000
# Hamma bir xil summa taklif qiladi. Qulf ishlasa: birinchi bid current_price
# ni bu qiymatga ko'taradi, qolganlari uchun min keyingi bid oshadi va
# ular "min increment" bilan rad etiladi -> aynan BITTA g'olib.
TARGET_BID = STARTING_PRICE + INCREMENT


def _seed_auction(db: Session) -> tuple[int, list[int]]:
    """Sotuvchi, N xaridor, faol auksion yaratadi. (auction_id, bidder_ids)."""
    seller = User(
        email="seller@race.test",
        hashed_password=hash_password(TEST_PASSWORD),
        full_name="Seller",
        role=UserRole.SELLER,
    )
    db.add(seller)
    db.flush()

    bidders = [
        User(
            email=f"bidder{i}@race.test",
            hashed_password=hash_password(TEST_PASSWORD),
            full_name=f"Bidder {i}",
            role=UserRole.USER,
        )
        for i in range(CONCURRENCY)
    ]
    db.add_all(bidders)
    db.flush()

    item = Item(
        seller_id=seller.id,
        title="Race item",
        condition=ItemCondition.USED,
        status=ItemStatus.ACTIVE,
        starting_price=STARTING_PRICE,
    )
    db.add(item)
    db.flush()

    now = datetime.now(UTC)
    auction = Auction(
        item_id=item.id,
        seller_id=seller.id,
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(days=1),
        status=AuctionStatus.ACTIVE,
        starting_price=STARTING_PRICE,
        current_price=STARTING_PRICE,
        minimum_bid_increment=INCREMENT,
    )
    db.add(auction)
    db.flush()

    bidder_ids = [b.id for b in bidders]
    auction_id = auction.id
    db.commit()
    return auction_id, bidder_ids


def test_parallel_bids_only_one_wins(db_session: Session, db_engine: Engine) -> None:
    auction_id, bidder_ids = _seed_auction(db_session)

    SessionMaker = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    barrier = threading.Barrier(CONCURRENCY)
    results: dict[int, str] = {}
    lock = threading.Lock()

    def place(bidder_id: int) -> None:
        # Har thread — o'z sessiyasi, o'z ulanishi. Aynan shu haqiqiy
        # raqobatni yuzaga keltiradi.
        session = SessionMaker()
        try:
            bidder = session.get(User, bidder_id)
            barrier.wait()  # hamma bir vaqtda otiladi
            try:
                BidService(session).place_bid(auction_id, bidder, BidCreate(amount=TARGET_BID))
                outcome = "ok"
            except Exception as exc:  # noqa: BLE001
                outcome = type(exc).__name__
            with lock:
                results[bidder_id] = outcome
        finally:
            session.close()

    threads = [threading.Thread(target=place, args=(bid,)) for bid in bidder_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [b for b, o in results.items() if o == "ok"]

    # 1) Aynan bitta bid muvaffaqiyatli.
    assert len(successes) == 1, f"kutilgan 1 g'olib, aslida {len(successes)}: {results}"

    # 2) DB holati buzilmagan — tekshirish uchun toza sessiya.
    check = SessionMaker()
    try:
        auction = check.get(Auction, auction_id)
        valid_bids = (
            check.query(Bid)
            .filter(Bid.auction_id == auction_id, Bid.status == BidStatus.VALID)
            .all()
        )
        assert auction.current_price == TARGET_BID
        assert auction.highest_bidder_id == successes[0]
        assert len(valid_bids) == 1
        assert valid_bids[0].bidder_id == successes[0]
    finally:
        check.close()
