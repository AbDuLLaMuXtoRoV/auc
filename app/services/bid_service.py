from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auction import Auction
from app.models.bid import Bid
from app.models.enums import AuctionStatus, BidStatus, ItemStatus, NotificationType
from app.models.user import User
from app.repositories.auction_repository import AuctionRepository
from app.schemas.bid import BidCreate
from app.services.auction_state import assert_transition
from app.services.notification_service import NotificationService


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

    def place_bid(
        self,
        auction_id: int,
        bidder: User,
        payload: BidCreate,
        ip: str | None = None,
        device_id: str | None = None,
    ) -> Bid:
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

        PROXY BIDDING (orqaga mos):
          - max_amount berilmasa — oddiy bid: ko'ringan narx = amount.
          - max_amount berilsa — keyingi raqib kelганда tizim leader nomidan
            avtomatik bir qadam yuqoriga ko'taradi (leader max'igacha).
        high_bidder_max HECH QACHON javobda oshkor bo'lmaydi.
        """
        try:
            auction = self.auctions.get_for_update(auction_id)
            if auction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Auction not found"
                )

            self._activate_if_started_locked(auction)
            self._validate_bid(auction, bidder, payload)

            returned_bid = self._resolve_bid(auction, bidder, payload)
            # Anti-fraud izlari — chaqiruvchining bid yozuviga (proxy'ga emas).
            returned_bid.ip = ip
            returned_bid.device_id = device_id
            auction.updated_at = datetime.now(UTC)
            self._apply_soft_close_extension(auction)

            self.db.add(auction)
            self.db.commit()
        except Exception:
            # Qulfni darhol bo'shatish — kutayotgan bidlar navbatda
            # keraksiz turmasin.
            self.db.rollback()
            raise

        self.db.refresh(returned_bid)
        return returned_bid

    def _resolve_bid(self, auction: Auction, bidder: User, payload: BidCreate) -> Bid:
        """Proxy bidding yechimi. Chaqiruvchiga qaytariladigan Bid'ni beradi.

        Uch holat:
          A) Leader avtomatik himoyalanadi — leader max chaqiruvchining
             ko'ringan bidini bir qadamdan ortiq qoplaydi. Chaqiruvchi bidi
             OUTBID yoziladi, leader nomidan is_proxy=True bid qo'shiladi,
             narx amount+step ga ko'tariladi, leader o'zgarmaydi.
          B) Chaqiruvchi yangi leader bo'ladi — narx = uning ko'ringan bidi,
             high_bidder_max = uning max_amount'i.

        Har holatda winning_bid.amount == current_price bo'lib qoladi, shu
        sababli close/order mantig'i o'zgarmaydi (yakuniy narx = winning bid).
        """
        amount = payload.amount
        max_amount = payload.max_amount if payload.max_amount is not None else payload.amount
        step = auction.minimum_bid_increment
        leader_id = auction.highest_bidder_id
        leader_max = auction.high_bidder_max

        caller_bid = Bid(
            auction_id=auction.id,
            bidder_id=bidder.id,
            amount=amount,
            max_amount=max_amount,
            is_proxy=False,
            status=BidStatus.VALID,
        )

        leader_defends = (
            leader_id is not None
            and leader_id != bidder.id
            and leader_max is not None
            and leader_max >= amount + step
        )

        if leader_defends:
            # Holat A: leader proxy himoyasi. Chaqiruvchi darhol ortda qoldi.
            caller_bid.status = BidStatus.OUTBID
            self.db.add(caller_bid)

            new_price = amount + step  # leader_max >= amount+step tekshirildi
            proxy_bid = Bid(
                auction_id=auction.id,
                bidder_id=leader_id,
                amount=new_price,
                max_amount=leader_max,
                is_proxy=True,
                status=BidStatus.VALID,
            )
            self._demote_current_winner(auction)
            self.db.add(proxy_bid)
            auction.current_price = new_price
            auction.winning_bid = proxy_bid
            # leader_id, high_bidder_max o'zgarmaydi
            self._notify_outbid(auction, bidder.id, new_price)
            return caller_bid

        # Holat B: chaqiruvchi yangi (yoki o'z narxini oshiruvchi) leader.
        self._demote_current_winner(auction)
        self.db.add(caller_bid)
        auction.current_price = amount
        auction.highest_bidder_id = bidder.id
        auction.high_bidder_max = max_amount
        auction.winning_bid = caller_bid
        # Eski leader (agar boshqa odam bo'lsa) ortda qoldi.
        if leader_id is not None and leader_id != bidder.id:
            self._notify_outbid(auction, leader_id, amount)
        return caller_bid

    def _demote_current_winner(self, auction: Auction) -> None:
        """Joriy yutuvchi bidni OUTBID qiladi (yangi yutuvchi belgilanishidan oldin)."""
        previous = auction.winning_bid
        if previous is not None:
            previous.status = BidStatus.OUTBID
            self.db.add(previous)

    def _notify_outbid(self, auction: Auction, user_id: int, new_price: int) -> None:
        """Ortda qolgan bidderga OUTBID bildirishnomasi (bid tranzaksiyasi ichida)."""
        NotificationService(self.db).create(
            user_id=user_id,
            type=NotificationType.OUTBID,
            title="Sizni ortda qoldirishdi",
            body="Auksionda taklifingiz ortda qoldi. Yangi taklif qo'ying.",
            payload={"auction_id": auction.id, "current_price": str(new_price)},
        )

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

        CHEKLOV: uzaytirish cheksiz emas. Auksion ko'pi bilan
        `max_soft_close_extensions` marta uzaytiriladi (har uzaytirishda
        `extension_count += 1`). Limitga yetganda oxirgi soniyadagi bid
        muddatni SURMAYDI — auksion o'z vaqtida yopiladi. Aks holda ikki
        raqib navbatma-navbat bid qo'yib auksionni cheksiz cho'zishi mumkin edi.
        """
        now = datetime.now(UTC)
        end_time = _as_utc(auction.end_time)
        seconds_until_close = (end_time - now).total_seconds()

        within_window = 0 < seconds_until_close <= settings.soft_close_window_seconds
        under_limit = auction.extension_count < settings.max_soft_close_extensions

        if within_window and under_limit:
            auction.end_time = end_time + timedelta(seconds=settings.soft_close_extension_seconds)
            auction.extension_count += 1
