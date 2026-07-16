from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.bid import Bid
from app.repositories.auction_repository import AuctionRepository
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
    auction = AuctionRepository(db).get(auction_id)
    if auction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found")
    return BidService(db).place_bid(auction, current_user, payload)
