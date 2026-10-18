"""Auksion tugashiga oz qolganda eslatma (ENDING_SOON).

Muddatli auksionning butun qiymati — oxirgi soatdagi raqobat. Kuzatuvchi
yoki ortda qolgan bidder lot tugayotganini bilmasa, u qaytib kelmaydi va
lot arzon ketadi (yoki umuman sotilmaydi). Shu sabab tugashdan
`ending_soon_lead_minutes` oldin kuzatuvchilar va bidderlarga BIR MARTA
eslatma ketadi: Telegram/push/in-app (`NotificationService.create`).

Takrorlanmaslik `auctions.ending_soon_notified_at` bilan ta'minlanadi;
anti-sniping muddatni sursa ham eslatma qayta yuborilmaydi.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auction import Auction
from app.models.enums import NotificationType
from app.money import format_soum
from app.repositories.auction_repository import AuctionRepository
from app.repositories.bid_repository import BidRepository
from app.repositories.watchlist_repository import WatchlistRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def notify_ending_soon(db: Session) -> int:
    """Eslatma vaqti kelgan auksionlar bo'yicha xabar yuboradi.

    Eslatilgan auksionlar sonini qaytaradi. Toza funksiya — closer tik'idan
    ham, Celery beat'dan ham chaqiriladi va to'g'ridan-to'g'ri testlanadi.

    Ikki bosqich: (1) auksionlar bitta UPDATE bilan band qilinib DARHOL commit
    qilinadi — qulf xabar yuborish paytida ushlanmaydi; (2) har auksion alohida
    tranzaksiyada xabarlanadi. Semantika "ko'pi bilan bir marta": bitta auksion
    xabari yiqilsa, u qayta yuborilmaydi (takroriy spam yo'q), qolganlari davom etadi.
    """
    now = datetime.now(UTC)
    lead = timedelta(minutes=settings.ending_soon_lead_minutes)
    try:
        claimed = AuctionRepository(db).claim_due_for_ending_soon(now, lead)
        db.commit()
    except Exception:
        db.rollback()
        raise

    for auction_id in claimed:
        try:
            auction = db.get(Auction, auction_id)
            if auction is not None:
                _notify_auction(db, auction)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("ENDING_SOON: auksion=%s xabarini yuborib bo'lmadi", auction_id)
    return len(claimed)


def _notify_auction(db: Session, auction: Auction) -> None:
    """Bitta auksion: kuzatuvchilar + tirik bidli foydalanuvchilar (sotuvchidan tashqari)."""
    bidder_ids = set(BidRepository(db).list_bidder_ids(auction.id))
    recipients = bidder_ids | set(WatchlistRepository(db).list_user_ids_for_auction(auction.id))
    recipients.discard(auction.seller_id)
    if not recipients:
        return

    title_text = auction.item.title if auction.item else "Mahsulot"
    price = f"{format_soum(auction.current_price)} soʻm"
    notifier = NotificationService(db)
    for user_id in sorted(recipients):
        if user_id == auction.highest_bidder_id:
            body = f"«{title_text}» — hozircha siz yetakchisiz. Joriy narx: {price}."
        elif user_id in bidder_ids:
            body = (
                f"«{title_text}» — taklifingiz ortda qolgan. Joriy narx: {price}. Oxirgi imkoniyat."
            )
        else:
            body = f"«{title_text}» tez orada tugaydi. Joriy narx: {price}."
        notifier.create(
            user_id=user_id,
            type=NotificationType.ENDING_SOON,
            title="Auksion tugashiga oz qoldi",
            body=body,
            payload={
                "auction_id": auction.id,
                "current_price": str(auction.current_price),
                "end_time": auction.end_time.isoformat(),
            },
        )
    logger.info("ENDING_SOON: auksion=%s, %s ta qabul qiluvchi", auction.id, len(recipients))
