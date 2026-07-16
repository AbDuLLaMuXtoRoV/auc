from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auction import Auction
from app.models.bid import Bid
from app.models.enums import AuctionStatus, BidStatus
from app.models.user import User
from app.schemas.bid import BidCreate
from app.services.auction_service import AuctionService


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class BidService:
    """Auction bid workflow.

    This is the extension point for max bid / proxy bidding. A later implementation can
    replace direct winning-bid updates with proxy bid calculation while keeping routes stable.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def place_bid(self, auction: Auction, bidder: User, payload: BidCreate) -> Bid:
        # TODO: Support proxy/max bids and bid retraction policies.
        auction = AuctionService(self.db).activate_if_started(auction)
        self._validate_bid(auction, bidder, payload)

        bid = Bid(auction_id=auction.id, bidder_id=bidder.id, amount=payload.amount)
        previous_winner = auction.winning_bid
        if previous_winner is not None:
            previous_winner.status = BidStatus.OUTBID
            self.db.add(previous_winner)

        auction.current_price = payload.amount
        auction.winning_bid = bid
        auction.highest_bidder_id = bidder.id
        auction.updated_at = datetime.now(UTC)

        self._apply_soft_close_extension(auction)

        self.db.add(bid)
        self.db.add(auction)
        self.db.commit()
        self.db.refresh(bid)
        return bid

    def _validate_bid(self, auction: Auction, bidder: User, payload: BidCreate) -> None:
        if auction.seller_id == bidder.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot bid on your own item",
            )
        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction is not active",
            )

        now = datetime.now(UTC)
        if _as_utc(auction.start_time) > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction has not started",
            )
        if _as_utc(auction.end_time) <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction has ended",
            )

        minimum_next_bid = auction.current_price + auction.minimum_bid_increment
        if payload.amount < minimum_next_bid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid must meet the minimum bid increment",
            )

    def _apply_soft_close_extension(self, auction: Auction) -> None:
        """Future anti-sniping hook.

        Later this can extend auction.end_time when a valid bid lands near the close.
        The method is intentionally a no-op in the initial skeleton.
        """
        now = datetime.now(UTC)
        end_time = _as_utc(auction.end_time)
        seconds_until_close = (end_time - now).total_seconds()

        if 0 < seconds_until_close <= settings.soft_close_window_seconds:
            auction.end_time = end_time + timedelta(seconds=settings.soft_close_extension_seconds)
