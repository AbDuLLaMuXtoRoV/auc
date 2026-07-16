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

    def activate_if_started(self, auction: Auction) -> Auction:
        now = datetime.now(UTC)
        if (
            auction.status == AuctionStatus.SCHEDULED
            and _as_utc(auction.start_time) <= now
            and _as_utc(auction.end_time) > now
        ):
            auction.status = AuctionStatus.ACTIVE
            auction.item.status = ItemStatus.ACTIVE
            return self.auctions.save(auction)
        return auction

    def close_auction(self, auction: Auction) -> Auction:
        # TODO: Move this workflow to a background job triggered by auction end_time.
        winning_bid = BidRepository(self.db).get_highest_valid_bid(auction.id)
        if winning_bid is None:
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
            # TODO: Notify the seller and bidders when reserve is not met.
            auction.status = AuctionStatus.RESERVE_NOT_MET
            auction.item.status = ItemStatus.CANCELLED
            self.db.add(auction)
            self.db.commit()
            self.db.refresh(auction)
            return auction

        auction.status = AuctionStatus.ENDED
        auction.item.status = ItemStatus.SOLD
        # TODO: Trigger notifications and payment authorization after winner assignment.
        self.db.add(auction)
        self.db.flush()
        OrderService(self.db).create_order_for_winning_auction(auction)
        self.db.commit()
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
