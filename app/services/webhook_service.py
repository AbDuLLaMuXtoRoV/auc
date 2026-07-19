from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.webhook import is_fresh
from app.repositories.webhook_repository import WebhookRepository


class WebhookService:
    """PSP webhook hodisalarini replay va dedup himoyasi bilan qayta ishlaydi.

    Ikki qatlamli himoya:
      1. Replay — hodisa vaqti juda eski bo'lsa (`is_fresh` False), rad etamiz.
         Imzo to'g'ri bo'lsa ham, eski (haqiqiy) webhook'ni qayta yuborish
         orqali hujum qilib bo'lmasligi uchun.
      2. Dedup — `(provider, event_id)` allaqachon yozilgan bo'lsa, hodisa
         qayta ishlanmaydi (idempotent). PSP bir xil hodisani bir necha marta
         yuborishi mumkin.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = WebhookRepository(db)

    def process(
        self,
        *,
        provider: str,
        event_id: str,
        timestamp: int,
        payload: dict,
    ) -> str:
        """Hodisani qayta ishlaydi. Natija: "processed" / "duplicate" / "stale".

        TODO (real PSP kelganda): hodisa turiga (`payload["type"]`) qarab
        tegishli payment holatini `provider_payment_id` bo'yicha yangilash
        (masalan hold captured -> PaymentStatus.CAPTURED). Hozircha bu yadro
        faqat replay + dedup himoyasini beradi; payment holatiga tegmaymiz.
        """
        now_ts = int(datetime.now(UTC).timestamp())
        if not is_fresh(timestamp, now_ts):
            return "stale"

        if self.repo.exists(provider, event_id):
            return "duplicate"

        event = self.repo.create(provider, event_id, payload)
        self.repo.mark_processed(event)
        self.db.commit()
        return "processed"
