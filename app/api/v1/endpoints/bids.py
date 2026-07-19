from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.rate_limit import RateLimiter
from app.core.request_meta import client_ip, device_id
from app.models.bid import Bid
from app.schemas.bid import BidCreate, BidRead
from app.services.bid_service import BidService

router = APIRouter()


@router.post(
    "/{auction_id}",
    response_model=BidRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter("bid", 60))],
)
def create_bid_for_auction(
    auction_id: int,
    payload: BidCreate,
    current_user: CurrentUser,
    db: DbSession,
    request: Request,
) -> Bid:
    return BidService(db).place_bid(
        auction_id, current_user, payload, ip=client_ip(request), device_id=device_id(request)
    )
