"""Auksionni avtomatik yopuvchi fon vazifasi (closer worker).

Ilgari auksion faqat sotuvchi qo'lda `POST /auctions/{id}/close` chaqirsa
yopilardi. Bu manfaatlar to'qnashuvi: agar natija sotuvchiga yoqmasa
(masalan narx past yoki reserve bajarilmagan), u auksionni umuman
yopmasligi mumkin edi — g'olib esa lotni kuta-kuta qoladi.

Yechim: `end_time` o'tgan har bir ACTIVE auksionni fon vazifasi
avtomatik yopadi. Yopish mantig'i (g'olib aniqlash, order yaratish,
FOR UPDATE qulf, state machine) `AuctionService.close_auction` da —
bu modul faqat "muddati o'tganlarni top va yop" orkestratsiyasini qiladi.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.auction import Auction
from app.models.enums import AuctionStatus
from app.services.auction_service import AuctionService

logger = logging.getLogger(__name__)


def close_due_auctions(db: Session) -> int:
    """Muddati o'tgan faol auksionlarni yopadi, yopilganlar sonini qaytaradi.

    Toza, fon loop'siz funksiya — to'g'ridan-to'g'ri testlanadi.

    `end_time <= now` va status ACTIVE bo'lgan auksionlar tanlanadi.
    Anti-sniping `end_time` ni kelajakka surgan bo'lsa, u shu shart
    bilan avtomatik chetlab o'tiladi (hali "muddati o'tgan" hisoblanmaydi).

    Har bir yopish `try/except` bilan o'raladi: worker HTTP kontekstida
    emas, shuning uchun poyga (parallel bid/close auksionni allaqachon
    ENDED qilib qo'ygan) `HTTPException` ko'tarsa ham butun loop
    to'xtamasligi kerak — xatoni log qilib keyingisiga o'tamiz.
    """
    now = datetime.now(UTC)
    due_ids = (
        db.execute(
            select(Auction.id)
            .where(Auction.status == AuctionStatus.ACTIVE)
            .where(Auction.end_time <= now)
        )
        .scalars()
        .all()
    )

    closed = 0
    for auction_id in due_ids:
        try:
            AuctionService(db).close_auction(auction_id)
            closed += 1
        except Exception:
            # Poyga yoki allaqachon yopilgan holat — kutilgan, o'tkazamiz.
            logger.warning("Auksion %s ni avtomatik yopish muvaffaqiyatsiz", auction_id)

    return closed


async def _closer_loop() -> None:
    """Davriy ravishda muddati o'tgan auksionlarni yopib turuvchi loop.

    Har tik'da YANGI sync sessiya ochiladi (uzoq yashovchi sessiya
    eskirgan ma'lumot ushlab qolmasin) va sync DB ishi `to_thread`
    orqali bajariladi — event loop bloklanmaydi.
    """
    interval = settings.auction_closer_interval_seconds
    logger.info("Auksion closer worker ishga tushdi (interval=%ss)", interval)
    while True:
        try:
            await asyncio.to_thread(_run_once)
        except Exception:
            logger.exception("Auksion closer tik'ida kutilmagan xato")
        await asyncio.sleep(interval)


def _run_once() -> None:
    """Bitta tik: sessiya ochib, yop, yop."""
    db = SessionLocal()
    try:
        closed = close_due_auctions(db)
        if closed:
            logger.info("Auksion closer %s ta auksionni yopdi", closed)
    finally:
        db.close()


def start_auction_closer() -> asyncio.Task | None:
    """Closer worker'ni ishga tushiradi (yoqilgan va test bo'lmasa).

    Testlarda ishga tushirilmaydi: fon vazifasi test bazasini yoki
    boshqa testlarning auksionlarini kutilmaganda o'zgartirib qo'ymasin.
    Qaytarilgan Task shutdown'da bekor qilinishi kerak.
    """
    if not settings.auction_closer_enabled or settings.environment == "test":
        return None
    return asyncio.create_task(_closer_loop())


async def stop_auction_closer(task: asyncio.Task | None) -> None:
    """Closer worker'ni to'xtatadi (shutdown'da chaqiriladi)."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
