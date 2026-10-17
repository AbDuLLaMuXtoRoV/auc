"""Email yuborish vazifasi (queue).

Verifikatsiya / parolni tiklash tokenlari email orqali yuboriladi (auth_service
dagi TODO). Real SMTP/provayder keyin ulanadi — hozircha log'ga yoziladi
(tashqi bog'liqliksiz), lekin chaqiruv joyi (auth) va queue tayyor.
"""

from __future__ import annotations

import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.email.send_email")
def send_email(to: str, subject: str, body: str) -> bool:
    """Email yuboradi (hozircha log). Yuborildi/yo'q qaytaradi."""
    # TODO: real SMTP / provayder (SES/SendGrid) shu yerda ulanadi.
    logger.info("email -> to=%s subject=%r", to, subject)
    logger.debug("email body: %s", body)
    return True
