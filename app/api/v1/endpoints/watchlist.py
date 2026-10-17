from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.watchlist import Watchlist
from app.schemas.watchlist import WatchlistCreate, WatchlistRead
from app.services.watchlist_service import WatchlistService

router = APIRouter()


@router.post("", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    payload: WatchlistCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Watchlist:
    """Auksionni kuzatuv ro'yxatiga qo'shish. Takror qo'shish idempotent."""
    return WatchlistService(db).add(current_user, payload.auction_id)


@router.get("", response_model=list[WatchlistRead])
def list_watchlist(
    current_user: CurrentUser,
    db: DbSession,
) -> list[Watchlist]:
    """Mening kuzatuvlarim."""
    return WatchlistService(db).list_mine(current_user)


@router.delete("/{auction_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    auction_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Auksionni kuzatuvdan olib tashlash. Faqat o'z kuzatuvi."""
    WatchlistService(db).remove(current_user, auction_id)
