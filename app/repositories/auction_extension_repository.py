from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auction_extension import AuctionExtension


class AuctionExtensionRepository:
    """Anti-sniping uzaytirishlar tarixi. Auksion dvigateli (soft-close)
    ishlatadi — hozir minimal yozish/o'qish."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        auction_id: int,
        old_end_time: datetime,
        new_end_time: datetime,
        triggered_by_bid_id: int | None,
    ) -> AuctionExtension:
        extension = AuctionExtension(
            auction_id=auction_id,
            old_end_time=old_end_time,
            new_end_time=new_end_time,
            triggered_by_bid_id=triggered_by_bid_id,
        )
        self.db.add(extension)
        self.db.flush()
        return extension

    def list_by_auction(self, auction_id: int) -> list[AuctionExtension]:
        statement = (
            select(AuctionExtension)
            .where(AuctionExtension.auction_id == auction_id)
            .order_by(AuctionExtension.created_at.asc())
        )
        return list(self.db.scalars(statement))
