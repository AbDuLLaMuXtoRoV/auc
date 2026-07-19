"""Anti-fraud signal tahlili — admin uchun READ-ONLY servis.

Bu servis hech qachon yozmaydi (faqat SELECT/agregat). Maqsad: bir
foydalanuvchi atrofidagi firibgarlik izlarini (ko'p akkaunt, shill halqasi,
bot-velocity) tez ko'rsatib, moderatorni qo'lda tekshiruvga yo'naltirish.

Signallar `bids` jadvalidagi anti-fraud izlaridan (ip, device_id) hosil
bo'ladi. Bironta so'rov foydalanuvchini bittalab yuklamaydi — hammasi
to'plam-agregat, shuning uchun N+1 yo'q.
"""

from datetime import timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session, aliased

from app.models.auction import Auction
from app.models.bid import Bid

# --- Chegara qiymatlari (oqilona, konservativ tanlangan) ------------------
#
# device_id — brauzer/qurilma barmoq izi, amalda ancha noyob. Shuning uchun
# bitta boshqa akkaunt bir device'dan bid qo'ysa ham allaqachon shubhali.
SHARED_DEVICE_THRESHOLD = 1
# IP kuchsizroq signal: uy Wi-Fi, mobil NAT, ofis bir IP ortida bo'lishi
# mumkin. 2 kishi tabiiy bo'lishi mumkin — 3+ akkaunt bir IP dan allaqachon
# anomaliya. Shuning uchun >= 2 BOSHQA akkaunt bo'lsa bayroq ko'tariladi.
SHARED_IP_THRESHOLD = 2
# Sotuvchi o'z lotini alt-akkaunt bilan ko'targani (shill) — bitta hodisa ham
# yetarlicha jiddiy.
SHILL_OVERLAP_THRESHOLD = 1
# 10 soniyada 3+ bid — odam qo'lda emas, skript/bot ehtimoli yuqori.
RAPID_BID_WINDOW = timedelta(seconds=10)
RAPID_BID_THRESHOLD = 3


class FraudService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def signals_for_user(self, user_id: int) -> dict:
        """Foydalanuvchi bo'yicha barcha firibgarlik signallarini hisoblaydi."""
        shared_device_user_ids = self._shared_dimension_user_ids(user_id, Bid.device_id)
        shared_ip_user_ids = self._shared_dimension_user_ids(user_id, Bid.ip)
        self_auction_ip_overlap = self._self_auction_overlap(user_id)
        bid_count = self._bid_count(user_id)
        distinct_auctions = self._distinct_auctions(user_id)
        rapid_bid_max_per_10s = self._rapid_bid_max(user_id)

        risk_flags = self._risk_flags(
            shared_device_user_ids=shared_device_user_ids,
            shared_ip_user_ids=shared_ip_user_ids,
            self_auction_ip_overlap=self_auction_ip_overlap,
            rapid_bid_max_per_10s=rapid_bid_max_per_10s,
        )

        return {
            "user_id": user_id,
            "shared_device_user_ids": shared_device_user_ids,
            "shared_ip_user_ids": shared_ip_user_ids,
            "self_auction_ip_overlap": self_auction_ip_overlap,
            "bid_count": bid_count,
            "distinct_auctions": distinct_auctions,
            "rapid_bid_max_per_10s": rapid_bid_max_per_10s,
            "risk_flags": risk_flags,
        }

    # -- individual signallar ------------------------------------------------

    def _shared_dimension_user_ids(self, user_id: int, column: InstrumentedAttribute) -> list[int]:
        """Berilgan o'lcham (ip yoki device_id) bo'yicha bir qiymatni ulashgan
        BOSHQA bidder_id'lar.

        Avval foydalanuvchining NULL bo'lmagan qiymatlari, so'ng o'sha
        qiymatlardan bid qo'ygan o'zga akkauntlar — bitta IN-quyi so'rov bilan.
        """
        my_values = select(column).where(Bid.bidder_id == user_id, column.isnot(None)).distinct()
        statement = (
            select(Bid.bidder_id)
            .where(
                column.in_(my_values),
                Bid.bidder_id != user_id,
                column.isnot(None),
            )
            .distinct()
            .order_by(Bid.bidder_id)
        )
        return list(self.db.scalars(statement))

    def _self_auction_overlap(self, user_id: int) -> int:
        """Foydalanuvchi bid qo'ygan auksionlar ichida, o'sha auksion
        SOTUVCHISI foydalanuvchi bilan bir IP yoki device ishlatgan holatlar
        (distinct auksion) soni.

        Sotuvchi o'z lotiga to'g'ridan-to'g'ri bid qo'yolmaydi (shill bloki),
        shuning uchun sotuvchining IP/device izi boshqa auksionlardagi
        bidlaridan olinadi. Moslik topilsa — alt-akkaunt orqali o'z lotini
        ko'tarayotgan bo'lishi ehtimoli.
        """
        my_ips = select(Bid.ip).where(Bid.bidder_id == user_id, Bid.ip.isnot(None)).distinct()
        my_devices = (
            select(Bid.device_id)
            .where(Bid.bidder_id == user_id, Bid.device_id.isnot(None))
            .distinct()
        )

        user_bid = aliased(Bid)  # foydalanuvchining bu auksiondagi bidi
        seller_bid = aliased(Bid)  # sotuvchining istalgan joydagi bidi

        statement = (
            select(func.count(func.distinct(Auction.id)))
            .select_from(Auction)
            .join(
                user_bid,
                and_(user_bid.auction_id == Auction.id, user_bid.bidder_id == user_id),
            )
            .join(seller_bid, seller_bid.bidder_id == Auction.seller_id)
            .where(
                Auction.seller_id != user_id,
                or_(
                    and_(seller_bid.ip.isnot(None), seller_bid.ip.in_(my_ips)),
                    and_(
                        seller_bid.device_id.isnot(None),
                        seller_bid.device_id.in_(my_devices),
                    ),
                ),
            )
        )
        return self.db.scalar(statement) or 0

    def _bid_count(self, user_id: int) -> int:
        return self.db.scalar(select(func.count(Bid.id)).where(Bid.bidder_id == user_id)) or 0

    def _distinct_auctions(self, user_id: int) -> int:
        return (
            self.db.scalar(
                select(func.count(func.distinct(Bid.auction_id))).where(Bid.bidder_id == user_id)
            )
            or 0
        )

    def _rapid_bid_max(self, user_id: int) -> int:
        """10 soniyalik siljuvchi oynada eng ko'p bid soni (velocity).

        Har bir bid uchun [t, t+10s) oynasidagi o'z bidlari sanaladi, so'ng
        shu sanoqlarning maksimumi olinadi. Bitta bid bo'lsa natija 1.
        """
        anchor = aliased(Bid)
        neighbor = aliased(Bid)
        per_window = (
            select(func.count(neighbor.id).label("cnt"))
            .select_from(anchor)
            .join(
                neighbor,
                and_(
                    neighbor.bidder_id == user_id,
                    neighbor.created_at >= anchor.created_at,
                    neighbor.created_at < anchor.created_at + RAPID_BID_WINDOW,
                ),
            )
            .where(anchor.bidder_id == user_id)
            .group_by(anchor.id)
            .subquery()
        )
        return self.db.scalar(select(func.max(per_window.c.cnt))) or 0

    # -- bayroqlar -----------------------------------------------------------

    def _risk_flags(
        self,
        *,
        shared_device_user_ids: list[int],
        shared_ip_user_ids: list[int],
        self_auction_ip_overlap: int,
        rapid_bid_max_per_10s: int,
    ) -> list[str]:
        flags: list[str] = []
        if len(shared_device_user_ids) >= SHARED_DEVICE_THRESHOLD:
            flags.append("shared_device")
        if len(shared_ip_user_ids) >= SHARED_IP_THRESHOLD:
            flags.append("shared_ip")
        if self_auction_ip_overlap >= SHILL_OVERLAP_THRESHOLD:
            flags.append("shill_ip_overlap")
        if rapid_bid_max_per_10s >= RAPID_BID_THRESHOLD:
            flags.append("high_velocity")
        return flags
