from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.handover import Handover


class HandoverRepository:
    """Handover yozuvlariga DB kirishi (select/insert/save)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, handover: Handover) -> Handover:
        self.db.add(handover)
        self.db.flush()
        return handover

    def get_by_order_id(self, order_id: int) -> Handover | None:
        statement = select(Handover).where(Handover.order_id == order_id)
        return self.db.scalar(statement)

    def save(self, handover: Handover) -> Handover:
        """Handover holatini yozadi (flush — commit chaqiruvchida)."""
        self.db.add(handover)
        self.db.flush()
        return handover
