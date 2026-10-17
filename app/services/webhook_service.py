from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.webhook import is_fresh
from app.repositories.webhook_repository import WebhookRepository
from app.services.payment_providers import map_psp_status
from app.services.payment_service import PaymentService


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

        Ikki qatlamli himoyadan (replay + dedup) so'ng hodisa PSP holatiga
        qarab payment/order'ga ULANADI: `provider_payment_id` bo'yicha to'lov
        topiladi va PSP e'lon qilgan holatga (haqiqat manbai) o'tkaziladi
        (`PaymentService.reconcile_from_webhook`). Hodisa yozuvi va payment
        o'zgarishi BITTA tranzaksiyada commit qilinadi — atomik.

        Noma'lum id / begona to'lov / taqiqlangan o'tish holatlarida payment
        o'zgarmaydi (webhook baribir "processed" — PSP retry qilmasin).
        """
        now_ts = int(datetime.now(UTC).timestamp())
        if not is_fresh(timestamp, now_ts):
            return "stale"

        if self.repo.exists(provider, event_id):
            return "duplicate"

        event = self.repo.create(provider, event_id, payload)
        self.repo.mark_processed(event)

        self._reconcile_payment(provider, event_id, payload)

        self.db.commit()
        return "processed"

    def _reconcile_payment(self, provider: str, event_id: str, payload: dict) -> None:
        """Hodisadan payment/order holatini yangilaydi (commit qilmaydi).

        Target holat FAQAT PSP ning avtoritetli `status` maydonidan olinadi
        (haqiqat manbai). `type` verbidan xulosa chiqarilmaydi — "release"
        (blokni bekor qilish -> CANCELLED_HOLD) va "released" (capture ->
        RELEASED) qarama-qarshi ma'noni bildirib, xato holatga sabab bo'ladi.
        Status yoki provider_payment_id bo'lmasa — faqat hodisa yozuvi qoladi.
        """
        provider_payment_id = payload.get("provider_payment_id") or payload.get("id")
        if not provider_payment_id:
            return

        target = map_psp_status(payload.get("status"))
        if target is None:
            return

        PaymentService(self.db).reconcile_from_webhook(
            provider=provider,
            provider_payment_id=str(provider_payment_id),
            target_status=target,
            event_id=event_id,
        )
