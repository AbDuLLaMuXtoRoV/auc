from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auction import Auction
from app.models.enums import AuctionStatus, ItemStatus
from app.models.item import Item
from app.models.order import Order
from app.models.user import User
from app.repositories.auction_repository import AuctionRepository
from app.repositories.bid_repository import BidRepository
from app.schemas.auction import AuctionCreate
from app.schemas.order import OrderRead
from app.services.auction_state import (
    SELLER_ALLOWED_TARGETS,
    InvalidAuctionTransition,
    assert_transition,
)
from app.services.order_service import OrderService


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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

        now = datetime.now(UTC)
        auction_status = (
            AuctionStatus.ACTIVE if _as_utc(payload.start_time) <= now else AuctionStatus.SCHEDULED
        )
        return self.auctions.create(seller, item, payload, auction_status)

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

            winning_bid = BidRepository(self.db).get_highest_valid_bid(auction.id)

            if winning_bid is None:
                assert_transition(auction.status, AuctionStatus.ENDED)
                auction.status = AuctionStatus.ENDED
                auction.winner_id = None
                auction.highest_bidder_id = None
                auction.item.status = ItemStatus.CANCELLED
                self.db.add(auction)
                self.db.commit()
                self.db.refresh(auction)
                return auction

            auction.winning_bid = winning_bid
            auction.highest_bidder_id = winning_bid.bidder_id
            auction.winner_id = winning_bid.bidder_id

            if auction.reserve_price is not None and winning_bid.amount < auction.reserve_price:
                # TODO: reserve bajarilmaganda sotuvchi va bidderlarni xabardor qil.
                assert_transition(auction.status, AuctionStatus.RESERVE_NOT_MET)
                auction.status = AuctionStatus.RESERVE_NOT_MET
                auction.item.status = ItemStatus.CANCELLED
                self.db.add(auction)
                self.db.commit()
                self.db.refresh(auction)
                return auction

            assert_transition(auction.status, AuctionStatus.ENDED)
            auction.status = AuctionStatus.ENDED
            auction.item.status = ItemStatus.SOLD
            # TODO: g'olib aniqlangach xabar + to'lov avtorizatsiyasi.
            self.db.add(auction)
            self.db.flush()
            OrderService(self.db).create_order_for_winning_auction(auction)
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
