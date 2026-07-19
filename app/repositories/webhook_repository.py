from datetime import UTC, datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.webhook_event import WebhookEvent


class WebhookRepository:
    """Qayta ishlangan webhook hodisalari ustidan DB kirishi (dedup uchun)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def exists(self, provider: str, event_id: str) -> bool:
        """`(provider, event_id)` juftligi allaqachon yozilganmi.

        NEGA: takroriy webhook (replay yoki PSP'ning qayta yuborishi) ni
        aniqlash — bir xil hodisa ikkinchi marta qayta ishlanmasligi kerak.
        """
        statement = select(
            exists().where(
                WebhookEvent.provider == provider,
                WebhookEvent.event_id == event_id,
            )
        )
        return bool(self.db.scalar(statement))

    def create(self, provider: str, event_id: str, payload: dict | None) -> WebhookEvent:
        event = WebhookEvent(provider=provider, event_id=event_id, payload=payload)
        self.db.add(event)
        return event

    def mark_processed(self, event: WebhookEvent) -> WebhookEvent:
        event.processed_at = datetime.now(UTC)
        self.db.add(event)
        return event
