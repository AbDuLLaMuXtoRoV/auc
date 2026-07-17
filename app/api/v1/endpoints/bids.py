from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.bid import Bid
from app.schemas.bid import BidCreate, BidRead
from app.services.bid_service import BidService

router = APIRouter()


@router.post("/{auction_id}", response_model=BidRead, status_code=status.HTTP_201_CREATED)
def create_bid_for_auction(
    auction_id: int,
    payload: BidCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Bid:
    return BidService(db).place_bid(auction_id, current_user, payload)
