from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.rate_limit import RateLimiter
from app.core.request_meta import client_ip, device_id
from app.models.auction import Auction
from app.models.bid import Bid
from app.models.enums import AuctionStatus
from app.repositories.auction_repository import AuctionRepository
from app.repositories.item_repository import ItemRepository
from app.schemas.auction import AuctionCreate, AuctionRead, AuctionStatusUpdate
from app.schemas.bid import BidCreate, BidRead
from app.services.auction_service import AuctionService
from app.services.bid_service import BidService

router = APIRouter()
AuctionStatusQuery = Annotated[AuctionStatus | None, Query(alias="status")]
SkipQuery = Annotated[int, Query(ge=0)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]


@router.post("", response_model=AuctionRead, status_code=status.HTTP_201_CREATED)
def create_item_auction(
    payload: AuctionCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Auction:
    item = ItemRepository(db).get(payload.item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your item")

    repository = AuctionRepository(db)
    if repository.item_has_auction(item.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item already has an auction",
        )
    return AuctionService(db).create_auction(current_user, item, payload)


@router.get("", response_model=list[AuctionRead])
def read_auctions(
    db: DbSession,
    status_filter: AuctionStatusQuery = AuctionStatus.ACTIVE,
    skip: SkipQuery = 0,
    limit: LimitQuery = 50,
) -> list[Auction]:
    return AuctionRepository(db).list(status=status_filter, skip=skip, limit=limit)


@router.get("/{auction_id}", response_model=AuctionRead)
def read_auction(auction_id: int, db: DbSession) -> Auction:
    auction = AuctionRepository(db).get(auction_id)
    if auction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found")
    return auction


@router.patch("/{auction_id}/status", response_model=AuctionRead)
def set_auction_status(
    auction_id: int,
    payload: AuctionStatusUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> Auction:
    return AuctionService(db).set_status_by_seller(auction_id, current_user, payload.status)


@router.post("/{auction_id}/close", response_model=AuctionRead)
def close_auction(
    auction_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Auction:
    auction = AuctionRepository(db).get(auction_id)
    if auction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found")
    if auction.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your auction")
    return AuctionService(db).close_auction(auction_id)


@router.post(
    "/{auction_id}/bids",
    response_model=BidRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter("bid", 60))],
)
def create_bid(
    auction_id: int,
    payload: BidCreate,
    current_user: CurrentUser,
    db: DbSession,
    request: Request,
) -> Bid:
    return BidService(db).place_bid(
        auction_id, current_user, payload, ip=client_ip(request), device_id=device_id(request)
    )
