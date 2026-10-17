from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.watchlist import Watchlist
from app.repositories.auction_repository import AuctionRepository
from app.repositories.watchlist_repository import WatchlistRepository


class WatchlistService:
    """Kuzatuv ro'yxati: auksionni qo'shish/o'chirish/ro'yxatlash.

    Qo'shish idempotent — mavjud kuzatuv qayta yaratilmaydi (unique buzilmaydi).
    O'chirishda faqat o'z kuzatuvi (egalik tekshiruvi).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.watchlist = WatchlistRepository(db)
        self.auctions = AuctionRepository(db)

    def add(self, user: User, auction_id: int) -> Watchlist:
        auction = self.auctions.get(auction_id)
        if auction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found")

        existing = self.watchlist.get(user.id, auction_id)
        if existing is not None:
            # Idempotent: takror qo'shish xato emas, mavjudini qaytaramiz.
            return existing

        entry = self.watchlist.create(user_id=user.id, auction_id=auction_id)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def remove(self, user: User, auction_id: int) -> None:
        entry = self.watchlist.get(user.id, auction_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist entry not found"
            )
        self.watchlist.delete(entry)
        self.db.commit()

    def list_mine(self, user: User) -> list[Watchlist]:
        return self.watchlist.list_by_user(user.id)
