from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auction import Auction
from app.models.bid import Bid
from app.models.enums import AuctionStatus, BidStatus, ItemStatus, NotificationType
from app.models.item import Item
from app.models.order import Order
from app.models.user import User
from app.realtime import manager
from app.repositories.auction_repository import AuctionRepository
from app.repositories.bid_repository import BidRepository
from app.repositories.item_repository import ItemRepository
from app.schemas.auction import AuctionCreate, AuctionRelist
from app.schemas.order import OrderRead
from app.services.auction_state import (
    SELLER_ALLOWED_TARGETS,
    InvalidAuctionTransition,
    assert_transition,
)
from app.services.notification_service import NotificationService
from app.services.order_service import OrderService

# Second-chance offer amal qilish muddati: reserve bajarilmagach sotuvchiga
# eng yuqori bidderga sotish taklifi shu muddat ichida ochiq turadi.
SECOND_CHANCE_TTL = timedelta(hours=24)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _validate_pricing(starting: int, reserve: int | None, buy_now: int | None) -> None:
    """Narxlar o'zaro mantiqiy bo'lishi shart (400).

    Buy-now boshlang'ich narxdan YUQORI bo'lishi kerak — teng bo'lsa auksion
    ma'nosiz (birinchi xaridor darhol qat'iy narxda oladi). Rezervdan past
    buy-now esa sotuvchi "shu narxdan pastga sotmayman" degan narxdan arzonga
    sotib yuborardi.
    """
    if reserve is not None and reserve < starting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reserve price cannot be below the starting price",
        )
    if buy_now is None:
        return
    if buy_now <= starting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buy now price must be above the starting price",
        )
    if reserve is not None and buy_now < reserve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buy now price cannot be below the reserve price",
        )


class AuctionService:
    """Winner resolution and settlement workflow.

    Future production work belongs here: reserve strategies, payment authorization,
    fraud checks, notifications, and background scheduling.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auctions = AuctionRepository(db)

    def create_auction(self, seller: User, item: Item, payload: AuctionCreate) -> Auction:
        allowed_item_statuses = {ItemStatus.DRAFT, ItemStatus.SCHEDULED}
        if item.status not in allowed_item_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction can only be created for a draft or scheduled item",
            )

        reserve = payload.reserve_price if payload.reserve_price is not None else item.reserve_price
        _validate_pricing(item.starting_price, reserve, payload.buy_now_price)

        now = datetime.now(UTC)
        auction_status = (
            AuctionStatus.ACTIVE if _as_utc(payload.start_time) <= now else AuctionStatus.SCHEDULED
        )
        return self.auctions.create(seller, item, payload, auction_status)

    def cancel_as_admin(self, auction_id: int) -> Auction:
        """Admin auksionni bekor qiladi (moderatsiya, firibgarlik).

        Sotuvchidan farqli, bidli auksionni ham bekor qila oladi. Qator FOR UPDATE
        bilan qulflanadi va o'tish state machine orqali (yakunlangan auksion — 409);
        tovar ham bekor qilinadi, aks holda e'lon katalogda "faol" bo'lib qolardi.
        """
        try:
            auction = self.auctions.get_for_update(auction_id)
            if auction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )
            try:
                assert_transition(auction.status, AuctionStatus.CANCELLED)
            except InvalidAuctionTransition as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            auction.status = AuctionStatus.CANCELLED
            auction.item.status = ItemStatus.CANCELLED
            self.db.add(auction)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(auction)
        return auction

    def buy_now(
        self,
        auction_id: int,
        buyer: User,
        *,
        ip: str | None = None,
        device_id: str | None = None,
        user_agent: str | None = None,
    ) -> Auction:
        """Xaridor lotni buy-now narxida darhol sotib oladi.

        Faqat birinchi taklif tushgunga qadar ochiq (keyin raqobat boshlangan,
        qat'iy narx uni to'xtatmasligi kerak). Natija oddiy g'alaba bilan bir
        xil: buy-now narxida VALID bid yoziladi, auksion ENDED bo'ladi va
        mavjud order oqimi (to'lov, escrow, buyer premium) o'zgarishsiz ishlaydi.

        Auksion qatori FOR UPDATE bilan qulflanadi — parallel bid yoki ikkinchi
        buy-now poyga qilmaydi: kechikkani qulfdan keyin ENDED holatni ko'rib 409 oladi.
        """
        try:
            auction = self.auctions.get_for_update(auction_id)
            if auction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )
            if auction.seller_id == buyer.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot buy your own item"
                )
            now = datetime.now(UTC)
            if auction.status != AuctionStatus.ACTIVE or _as_utc(auction.end_time) <= now:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Auction is not active"
                )
            if auction.buy_now_price is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Buy now is not available for this auction",
                )
            bids = BidRepository(self.db)
            if bids.get_highest_active_bid(auction.id) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Buy now is closed once bidding has started",
                )

            price = auction.buy_now_price
            bid = Bid(
                auction_id=auction.id,
                bidder_id=buyer.id,
                amount=price,
                max_amount=price,
                is_proxy=False,
                status=BidStatus.VALID,
                ip=ip,
                device_id=device_id,
                user_agent=user_agent,
            )
            self.db.add(bid)
            self.db.flush()

            auction.current_price = price
            auction.highest_bidder_id = buyer.id
            auction.high_bidder_max = price
            auction.winner_id = buyer.id
            auction.winning_bid = bid
            auction.bid_count = bids.count_bids(auction.id)
            auction.unique_bidder_count = bids.count_distinct_bidders(auction.id)

            assert_transition(auction.status, AuctionStatus.ENDED)
            auction.status = AuctionStatus.ENDED
            auction.closed_at = now
            # Muddatdan oldin yakunlandi: end_time haqiqiy tugash vaqtiga tenglanadi
            # (ro'yxat tartibi, sanoq). Asl muddat original_end_time'da qoladi.
            auction.end_time = now
            auction.item.status = ItemStatus.SOLD
            self.db.add(auction)
            self.db.flush()
            OrderService(self.db).create_order_for_winning_auction(auction)

            notifier = NotificationService(self.db)
            notifier.create(
                user_id=buyer.id,
                type=NotificationType.WON,
                title="Lotni sotib oldingiz",
                body="Mahsulot «hoziroq sotib olish» narxida sizniki. To'lovni amalga oshiring.",
                payload={"auction_id": auction.id, "final_price": str(price)},
            )
            notifier.create(
                user_id=auction.seller_id,
                type=NotificationType.SOLD,
                title="Mahsulotingiz sotildi",
                body="Xaridor lotni «hoziroq sotib olish» narxida sotib oldi.",
                payload={"auction_id": auction.id, "final_price": str(price)},
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(auction)
        # Kuzatuvchilar sahifasi darhol "yakunlangan" holatga o'tsin (best-effort).
        manager.broadcast_threadsafe(
            auction_id,
            {
                "type": "BUY_NOW",
                "auction_id": auction_id,
                "current_price": str(auction.current_price),
                "highest_bidder_id": auction.highest_bidder_id,
                "end_time": _as_utc(auction.end_time).isoformat(),
            },
        )
        return auction

    def relist(self, auction_id: int, seller: User, payload: AuctionRelist) -> Auction:
        """Sotilmagan lotni yangi narx/muddat bilan qayta joylaydi.

        Faqat sotilmay tugagan auksion: ENDED + g'olibsiz (bid bo'lmagan) yoki
        RESERVE_NOT_MET. Har item'da bitta auksion bo'lgani uchun e'lon nusxa
        ko'chiriladi (yangi item + yangi ACTIVE auksion, bitta tranzaksiyada).

        RESERVE_NOT_MET'da ochiq second-chance taklifi YOPILADI: aks holda
        sotuvchi qayta joylab, keyin eski taklifni ham qabul qilib, bitta
        tovarni ikki xaridorga sotishi mumkin edi.

        Eski auksion FOR UPDATE bilan qulflanadi — ikki parallel relist
        navbatma-navbat bajariladi, ikkinchisi tayyor nusxani ko'rib 409 oladi
        (items.relisted_from_id UNIQUE — oxirgi himoya qatlami).
        """
        try:
            old = self.auctions.get_for_update(auction_id)
            if old is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )
            if old.seller_id != seller.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Not your auction"
                )
            unsold = (
                old.status == AuctionStatus.ENDED and old.winner_id is None
            ) or old.status == AuctionStatus.RESERVE_NOT_MET
            if not unsold:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only an unsold auction can be relisted",
                )
            items = ItemRepository(self.db)
            if items.get_relist_of(old.item_id) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This listing has already been relisted",
                )
            _validate_pricing(payload.starting_price, payload.reserve_price, payload.buy_now_price)

            now = datetime.now(UTC)
            if (
                old.second_chance_expires_at is not None
                and _as_utc(old.second_chance_expires_at) > now
            ):
                old.second_chance_expires_at = now
                self.db.add(old)

            new_item = items.clone_for_relist(
                old.item,
                starting_price=payload.starting_price,
                reserve_price=payload.reserve_price,
            )
            create = AuctionCreate(
                item_id=new_item.id,
                start_time=now,
                duration_days=payload.duration_days,
                minimum_bid_increment=payload.minimum_bid_increment,
                reserve_price=payload.reserve_price,
                buy_now_price=payload.buy_now_price,
            )
            # Repository create bitta commit bilan hammasini yozadi (eski
            # auksion, nusxa item, yangi auksion) — qisman holat qolmaydi.
            return self.auctions.create(seller, new_item, create, AuctionStatus.ACTIVE)
        except Exception:
            self.db.rollback()
            raise

    def set_status_by_seller(self, auction_id: int, seller: User, target: AuctionStatus) -> Auction:
        """Sotuvchi qo'lda holat o'zgartiradi (amalda: bekor qilish).

        Ilgari bu endpoint sotuvchiga ISTALGAN holatni yozishga ruxsat
        berardi — jonli auksionni `ended` qilib order/g'olib oqimini
        chetlab o'tish, yoki bidli auksionni `cancelled` qilib bidlarni
        kuydirish mumkin edi. Endi:
          - faqat SELLER_ALLOWED_TARGETS (bekor qilish) ruxsat etiladi
          - o'tish state machine bilan tekshiriladi
          - bidli auksionni bekor qilib bo'lmaydi
        Auksion qatori FOR UPDATE bilan qulflanadi — bekor qilish va
        parallel bid o'zaro poyga qilmaydi.
        """
        try:
            auction = self.auctions.get_for_update(auction_id)
            if auction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )
            if auction.seller_id != seller.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Not your auction"
                )
            if target not in SELLER_ALLOWED_TARGETS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Seller can only cancel an auction",
                )

            try:
                assert_transition(auction.status, target)
            except InvalidAuctionTransition as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

            has_bids = BidRepository(self.db).get_highest_valid_bid(auction.id) is not None
            if has_bids:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot cancel an auction that already has bids",
                )

            auction.status = target
            auction.item.status = ItemStatus.CANCELLED
            self.db.add(auction)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(auction)
        return auction

    def close_auction(self, auction_id: int) -> Auction:
        """Auksionni yopadi: g'olibni aniqlab, order yaratadi.

        # TODO: fon vazifasiga ko'chirilsin (end_time bo'yicha avtomatik).

        Auksion qatori FOR UPDATE bilan qulflanadi — yopish paytida
        parallel bid kelib g'olibni o'zgartira olmaydi. Faqat ACTIVE
        auksion yopiladi (idempotent: qayta yopish yoki boshlanmaganini
        yopish 409 beradi). Holat o'zgarishlari state machine orqali.
        """
        try:
            auction = self.auctions.get_for_update(auction_id)
            if auction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )
            if auction.status != AuctionStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only an active auction can be closed",
                )

            now = datetime.now(UTC)
            winning_bid = BidRepository(self.db).get_highest_valid_bid(auction.id)

            if winning_bid is None:
                assert_transition(auction.status, AuctionStatus.ENDED)
                auction.status = AuctionStatus.ENDED
                auction.winner_id = None
                auction.highest_bidder_id = None
                auction.closed_at = now
                auction.item.status = ItemStatus.CANCELLED
                self.db.add(auction)
                self.db.commit()
                self.db.refresh(auction)
                return auction

            auction.winning_bid = winning_bid
            auction.highest_bidder_id = winning_bid.bidder_id
            auction.winner_id = winning_bid.bidder_id

            if auction.reserve_price is not None and winning_bid.amount < auction.reserve_price:
                # Reserve bajarilmadi: auksionni RESERVE_NOT_MET qilamiz va
                # sotuvchiga second-chance taklif beramiz — u eng yuqori bidderga
                # sotishga rozi bo'lsa (24 soat ichida) order yaratiladi.
                assert_transition(auction.status, AuctionStatus.RESERVE_NOT_MET)
                auction.status = AuctionStatus.RESERVE_NOT_MET
                auction.closed_at = now
                auction.second_chance_offered_at = now
                auction.second_chance_expires_at = now + SECOND_CHANCE_TTL
                auction.item.status = ItemStatus.CANCELLED
                self.db.add(auction)
                NotificationService(self.db).create(
                    user_id=auction.seller_id,
                    type=NotificationType.SECOND_CHANCE,
                    title="Rezerv narxga yetilmadi",
                    body=(
                        "Eng yuqori taklif rezerv narxdan past. Xohlasangiz eng yuqori "
                        "bidderga shu narxda sotishingiz mumkin (24 soat ichida)."
                    ),
                    payload={
                        "auction_id": auction.id,
                        "highest_bid": str(winning_bid.amount),
                        "expires_at": auction.second_chance_expires_at.isoformat(),
                    },
                )
                self.db.commit()
                self.db.refresh(auction)
                return auction

            assert_transition(auction.status, AuctionStatus.ENDED)
            auction.status = AuctionStatus.ENDED
            auction.closed_at = now
            auction.item.status = ItemStatus.SOLD
            self.db.add(auction)
            self.db.flush()
            OrderService(self.db).create_order_for_winning_auction(auction)
            # G'olib va sotuvchi xabardor qilinadi (tranzaksiya ichida, atomik).
            notifier = NotificationService(self.db)
            notifier.create(
                user_id=winning_bid.bidder_id,
                type=NotificationType.WON,
                title="Auksionda yutdingiz!",
                body="Tabriklaymiz — mahsulotni yutib oldingiz. To'lovni amalga oshiring.",
                payload={"auction_id": auction.id, "final_price": str(auction.current_price)},
            )
            notifier.create(
                user_id=auction.seller_id,
                type=NotificationType.SOLD,
                title="Mahsulotingiz sotildi",
                body="Auksioningiz g'olib bilan yakunlandi.",
                payload={"auction_id": auction.id, "final_price": str(auction.current_price)},
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(auction)
        return auction

    def accept_second_chance(self, auction_id: int, seller: User) -> Auction:
        """Sotuvchi second-chance taklifni qabul qiladi — eng yuqori bidderga sotadi.

        Reserve bajarilmagach (RESERVE_NOT_MET) sotuvchi taklif muddati (24 soat)
        ichida rozi bo'lsa: auksion ENDED bo'ladi, g'olib = eng yuqori VALID
        bidder, order yaratiladi (mavjud close oqimi bilan bir xil), g'olib va
        sotuvchi xabardor qilinadi. Muddat o'tgan yoki holat noto'g'ri bo'lsa 409.

        Auksion qatori FOR UPDATE bilan qulflanadi.
        """
        try:
            auction = self.auctions.get_for_update(auction_id)
            if auction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )
            if auction.seller_id != seller.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Not your auction"
                )
            if auction.status != AuctionStatus.RESERVE_NOT_MET:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No active second-chance offer for this auction",
                )

            now = datetime.now(UTC)
            if (
                auction.second_chance_expires_at is None
                or _as_utc(auction.second_chance_expires_at) <= now
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Second-chance offer has expired",
                )

            winning_bid = BidRepository(self.db).get_highest_valid_bid(auction.id)
            if winning_bid is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No valid bids to accept",
                )

            auction.winning_bid = winning_bid
            auction.highest_bidder_id = winning_bid.bidder_id
            auction.winner_id = winning_bid.bidder_id

            assert_transition(auction.status, AuctionStatus.ENDED)
            auction.status = AuctionStatus.ENDED
            auction.closed_at = now
            auction.item.status = ItemStatus.SOLD
            self.db.add(auction)
            self.db.flush()
            OrderService(self.db).create_order_for_winning_auction(auction)

            notifier = NotificationService(self.db)
            notifier.create(
                user_id=winning_bid.bidder_id,
                type=NotificationType.WON,
                title="Auksionda yutdingiz!",
                body="Sotuvchi taklifingizni qabul qildi. To'lovni amalga oshiring.",
                payload={"auction_id": auction.id, "final_price": str(auction.current_price)},
            )
            notifier.create(
                user_id=auction.seller_id,
                type=NotificationType.SOLD,
                title="Mahsulotingiz sotildi",
                body="Second-chance taklif qabul qilindi — auksion g'olib bilan yakunlandi.",
                payload={"auction_id": auction.id, "final_price": str(auction.current_price)},
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(auction)
        return auction

    def get_or_create_order_for_winner(self, auction: Auction) -> Order | None:
        if auction.winner_id is None:
            return None
        return OrderService(self.db).create_order_for_winning_auction(auction)


def serialize_order(order: Order | None) -> OrderRead | None:
    if order is None:
        return None
    return OrderRead.model_validate(order)


AuctionSettlementService = AuctionService
