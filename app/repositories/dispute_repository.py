from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dispute import Dispute
from app.models.enums import DisputeStatus

# Nizo hali "ochiq" hisoblanadigan holatlar: bularda pul muzlab turadi,
# shu order uchun ikkinchi nizo ochib bo'lmaydi.
OPEN_STATUSES = (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW)


class DisputeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        order_id: int,
        payment_id: int,
        opened_by: int,
        reason,
        description: str | None,
    ) -> Dispute:
        dispute = Dispute(
            order_id=order_id,
            payment_id=payment_id,
            opened_by=opened_by,
            reason=reason,
            description=description,
            status=DisputeStatus.OPEN,
        )
        self.db.add(dispute)
        self.db.flush()
        return dispute

    def get(self, dispute_id: int) -> Dispute | None:
        return self.db.get(Dispute, dispute_id)

    def get_open_by_order(self, order_id: int) -> Dispute | None:
        """Order uchun hali hal qilinmagan (OPEN/UNDER_REVIEW) nizo."""
        statement = select(Dispute).where(
            Dispute.order_id == order_id,
            Dispute.status.in_(OPEN_STATUSES),
        )
        return self.db.scalar(statement)

    def list_by_user(self, user_id: int) -> list[Dispute]:
        statement = (
            select(Dispute).where(Dispute.opened_by == user_id).order_by(Dispute.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def list_by_status(self, statuses) -> list[Dispute]:
        statement = (
            select(Dispute).where(Dispute.status.in_(statuses)).order_by(Dispute.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def save(self, dispute: Dispute) -> Dispute:
        self.db.add(dispute)
        self.db.flush()
        return dispute
