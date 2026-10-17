from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist


class WatchlistRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int, auction_id: int) -> Watchlist | None:
        statement = select(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.auction_id == auction_id,
        )
        return self.db.scalar(statement)

    def create(self, *, user_id: int, auction_id: int) -> Watchlist:
        entry = Watchlist(user_id=user_id, auction_id=auction_id)
        self.db.add(entry)
        self.db.flush()
        return entry

    def delete(self, entry: Watchlist) -> None:
        self.db.delete(entry)
        self.db.flush()

    def list_by_user(self, user_id: int) -> list[Watchlist]:
        statement = (
            select(Watchlist)
            .where(Watchlist.user_id == user_id)
            .order_by(Watchlist.created_at.desc())
        )
        return list(self.db.scalars(statement))
