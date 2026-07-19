"""Auto-complete fon vazifasi: xaridor sukut saqlasa order'ni yakunlaydi.

Escrow oqimi: hold qilingandan keyin xaridor tovarni tasdiqlashi kerak
(capture). Agar u sukut saqlasa, pul PSP'da abadiy bloklanib qolmasligi
kerak. `orders.auto_complete_at` (hold paytida now + 72 soat) o'tgach,
bu worker avtomatik capture qiladi — pul sotuvchiga o'tadi.

Capture mantig'i (state machine, audit, idempotentlik) PaymentService'da.
Bu modul faqat "muddati o'tgan hold'larni top va capture qil" qiladi.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import OrderStatus, PaymentStatus
from app.models.order import Order
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)


def auto_complete_due_orders(db: Session) -> int:
    """Muddati o'tgan hold'larni capture qiladi, soni qaytadi.

    Toza, fon loop'siz funksiya — to'g'ridan-to'g'ri testlanadi.
    `auto_complete_at <= now` va status PICKUP_PENDING (ya'ni hold qilingan,
    hali tasdiqlanmagan) order'lar tanlanadi.
    """
    now = datetime.now(UTC)
    due_order_ids = (
        db.execute(
            select(Order.id)
            .where(Order.status == OrderStatus.PICKUP_PENDING)
            .where(Order.auto_complete_at.is_not(None))
            .where(Order.auto_complete_at <= now)
        )
        .scalars()
        .all()
    )

    completed = 0
    payments = PaymentRepository(db)
    for order_id in due_order_ids:
        payment = payments.get_latest_by_order(order_id)
        if payment is None or payment.status != PaymentStatus.HELD:
            continue
        try:
            # actor=None: tizim (worker) qildi. Kalit deterministik —
            # takroriy tik ham xavfsiz (capture allaqachon RELEASED bo'lsa no-op).
            PaymentService(db).capture_payment(payment.id, f"auto-capture:{payment.id}", actor=None)
            completed += 1
        except Exception:
            logger.warning("Order %s ni avtomatik yakunlash muvaffaqiyatsiz", order_id)

    return completed


async def _auto_complete_loop() -> None:
    interval = settings.auto_complete_interval_seconds
    logger.info("Auto-complete worker ishga tushdi (interval=%ss)", interval)
    while True:
        try:
            await asyncio.to_thread(_run_once)
        except Exception:
            logger.exception("Auto-complete tik'ida kutilmagan xato")
        await asyncio.sleep(interval)


def _run_once() -> None:
    db = SessionLocal()
    try:
        done = auto_complete_due_orders(db)
        if done:
            logger.info("Auto-complete %s ta order'ni yakunladi", done)
    finally:
        db.close()


def start_auto_complete() -> asyncio.Task | None:
    """Auto-complete worker'ni ishga tushiradi (yoqilgan va test bo'lmasa)."""
    if not settings.auto_complete_enabled or settings.environment == "test":
        return None
    return asyncio.create_task(_auto_complete_loop())


async def stop_auto_complete(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
