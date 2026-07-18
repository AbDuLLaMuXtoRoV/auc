from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auction import Auction
from app.models.enums import AuctionStatus, ItemStatus
from app.models.item import Item
from app.models.user import User
from app.schemas.auction import AuctionCreate


class AuctionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        seller: User,
        item: Item,
        payload: AuctionCreate,
        status: AuctionStatus,
    ) -> Auction:
        auction = Auction(
            item_id=item.id,
            seller_id=seller.id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            duration_days=payload.duration_days,
            status=status,
            starting_price=item.starting_price,
            current_price=item.starting_price,
            minimum_bid_increment=payload.minimum_bid_increment,
            reserve_price=payload.reserve_price
            if payload.reserve_price is not None
            else item.reserve_price,
        )
        item.status = ItemStatus.ACTIVE if status == AuctionStatus.ACTIVE else ItemStatus.SCHEDULED
        self.db.add(auction)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(auction)
        return auction

    def list(
        self,
        *,
        status: AuctionStatus | None = AuctionStatus.ACTIVE,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Auction]:
        statement = select(Auction).order_by(Auction.end_time.asc()).offset(skip).limit(limit)
        if status is not None:
            statement = statement.where(Auction.status == status)
        return list(self.db.scalars(statement))

    def get(self, auction_id: int) -> Auction | None:
        return self.db.get(Auction, auction_id)

    def get_for_update(self, auction_id: int) -> Auction | None:
        """Auksion qatorini QULFLAB o'qiydi (SELECT ... FOR UPDATE).

        Bid oqimi uchun. Qulf tranzaksiya tugaguncha (commit/rollback)
        ushlanadi — shu vaqt ichida boshqa tranzaksiya shu qatorni
        o'qiy olmaydi, navbatda kutadi.

        Qulfsiz "o'qi -> tekshir -> yoz" ketma-ketligi lost update beradi:
        ikki bid bir xil current_price ni o'qiydi, ikkalasi ham
        validatsiyadan o'tadi, oxirgi yozuvchi g'olib bo'ladi — natijada
        pastroq taklif yutib, yuqori bid yo'qoladi.

        MUHIM: chaqiruvchi qulf o'rnatilgandan keyin commit QILMASLIGI
        kerak — har qanday commit qulfni bo'shatadi.
        """
        statement = select(Auction).where(Auction.id == auction_id).with_for_update()
        return self.db.scalars(statement).one_or_none()

    def item_has_auction(self, item_id: int) -> bool:
        statement = select(Auction.id).where(Auction.item_id == item_id)
        return self.db.scalar(statement) is not None
