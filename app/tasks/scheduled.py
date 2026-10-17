"""Davriy (Celery beat) vazifalar: auksion yopish va auto-complete.

Yopish/capture mantig'i o'zgarmaydi — mavjud toza funksiyalar
(`close_due_auctions`, `auto_complete_due_orders`) qayta ishlatiladi. Bu yerda
faqat "Celery kontekstida yangi DB sessiya ochib chaqirish" bor.
"""

from __future__ import annotations

import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.auction_closer import close_due_auctions
from app.services.auto_complete import auto_complete_due_orders

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.scheduled.close_due_auctions_task")
def close_due_auctions_task() -> int:
    """Muddati o'tgan faol auksionlarni yopadi. Yopilganlar sonini qaytaradi."""
    db = SessionLocal()
    try:
        closed = close_due_auctions(db)
        if closed:
            logger.info("Celery: %s ta auksion yopildi", closed)
        return closed
    finally:
        db.close()


@celery_app.task(name="app.tasks.scheduled.auto_complete_orders_task")
def auto_complete_orders_task() -> int:
    """Muddati o'tgan hold'larni capture qiladi. Yakunlanganlar sonini qaytaradi."""
    db = SessionLocal()
    try:
        done = auto_complete_due_orders(db)
        if done:
            logger.info("Celery: %s ta order avtomatik yakunlandi", done)
        return done
    finally:
        db.close()
