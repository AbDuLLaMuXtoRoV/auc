from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.enums import BidStatus


class BidRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, bid: Bid) -> Bid:
        self.db.add(bid)
        self.db.commit()
        self.db.refresh(bid)
        return bid

    def get_highest_valid_bid(self, auction_id: int) -> Bid | None:
        statement = (
            select(Bid)
            .where(Bid.auction_id == auction_id, Bid.status == BidStatus.VALID)
            .order_by(Bid.amount.desc(), Bid.created_at.asc())
            .limit(1)
        )
        return self.db.scalar(statement)
