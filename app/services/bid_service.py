from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auction import Auction
from app.models.bid import Bid
from app.models.enums import AuctionStatus, BidStatus, ItemStatus
from app.models.user import User
from app.repositories.auction_repository import AuctionRepository
from app.schemas.bid import BidCreate
from app.services.auction_state import assert_transition


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class BidService:
    """Bid qo'yish oqimi.

    Proxy/max-bid uchun kengaytirish nuqtasi shu yerda.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auctions = AuctionRepository(db)

    def place_bid(self, auction_id: int, bidder: User, payload: BidCreate) -> Bid:
        """Bid qo'yadi. ATOMIK — race condition'siz.

        Butun mantiq BITTA tranzaksiyada:
          1) auksion qatorini FOR UPDATE bilan qulflab qayta o'qiydi
          2) validatsiya (qulf ostida — o'qilgan narx eskirmaydi)
          3) yozish
          4) bitta commit

        Qulf o'rnatilgach commit qilinmaydi: har commit qulfni bo'shatadi
        va "o'qi -> tekshir -> yoz" oynasi yana ochilib qoladi. Aynan shu
        sababli auksionni aktivlashtirish ham bu yerda commit'siz
        bajariladi (_activate_if_started_locked).
        """
        # TODO: proxy/max bid — docs/AUCTION_ENGINE.md
        try:
            auction = self.auctions.get_for_update(auction_id)
            if auction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )

            self._activate_if_started_locked(auction)
            self._validate_bid(auction, bidder, payload)

            bid = Bid(auction_id=auction.id, bidder_id=bidder.id, amount=payload.amount)
            previous_winner = auction.winning_bid
            if previous_winner is not None:
                previous_winner.status = BidStatus.OUTBID
                self.db.add(previous_winner)

            auction.current_price = payload.amount
            auction.winning_bid = bid
            auction.highest_bidder_id = bidder.id
            auction.updated_at = datetime.now(UTC)

            self._apply_soft_close_extension(auction)

            self.db.add(bid)
            self.db.add(auction)
            self.db.commit()
        except Exception:
            # Qulfni darhol bo'shatish — kutayotgan bidlar navbatda
            # keraksiz turmasin.
            self.db.rollback()
            raise

        self.db.refresh(bid)
        return bid

    def _activate_if_started_locked(self, auction: Auction) -> None:
        """SCHEDULED -> ACTIVE, commit QILMASDAN.

        Auksion boshlanish vaqti o'tgan bo'lsa aktivlashtiradi. Commit
        qilinmaydi — aks holda bid oqimidagi FOR UPDATE qulfi bo'shab,
        race condition oynasi ochilib qoladi.
        """
        now = datetime.now(UTC)
        if (
            auction.status == AuctionStatus.SCHEDULED
            and _as_utc(auction.start_time) <= now
            and _as_utc(auction.end_time) > now
        ):
            assert_transition(auction.status, AuctionStatus.ACTIVE)
            auction.status = AuctionStatus.ACTIVE
            auction.item.status = ItemStatus.ACTIVE
            self.db.add(auction)

    def _validate_bid(self, auction: Auction, bidder: User, payload: BidCreate) -> None:
        if auction.seller_id == bidder.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot bid on your own item",
            )
        if auction.status != AuctionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction is not active",
            )

        now = datetime.now(UTC)
        if _as_utc(auction.start_time) > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction has not started",
            )
        if _as_utc(auction.end_time) <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction has ended",
            )

        minimum_next_bid = auction.current_price + auction.minimum_bid_increment
        if payload.amount < minimum_next_bid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid must meet the minimum bid increment",
            )

    def _apply_soft_close_extension(self, auction: Auction) -> None:
        """Anti-sniping: tugashga oz qolganda kelgan bid muddatni uzaytiradi.

        Tugashga `soft_close_window_seconds` (120s) yoki kamroq qolganda
        valid bid kelsa, `end_time` `soft_close_extension_seconds` (120s)
        ga suriladi. Maqsad: oxirgi soniyada urib olishning (sniping)
        oldini olish — har kim javob berishga ulguradi.
        """
        now = datetime.now(UTC)
        end_time = _as_utc(auction.end_time)
        seconds_until_close = (end_time - now).total_seconds()

        if 0 < seconds_until_close <= settings.soft_close_window_seconds:
            auction.end_time = end_time + timedelta(seconds=settings.soft_close_extension_seconds)
