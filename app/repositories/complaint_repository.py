from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus, ComplaintTargetType


class ComplaintRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        reporter_id: int,
        target_type: ComplaintTargetType,
        target_id: int,
        reason: str,
        description: str | None,
    ) -> Complaint:
        complaint = Complaint(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            description=description,
            status=ComplaintStatus.OPEN,
        )
        self.db.add(complaint)
        self.db.flush()
        return complaint

    def get(self, complaint_id: int) -> Complaint | None:
        return self.db.get(Complaint, complaint_id)

    def list_all(self, status: ComplaintStatus | None = None) -> list[Complaint]:
        statement = select(Complaint)
        if status is not None:
            statement = statement.where(Complaint.status == status)
        statement = statement.order_by(Complaint.created_at.desc())
        return list(self.db.scalars(statement))

    def save(self, complaint: Complaint) -> Complaint:
        self.db.add(complaint)
        self.db.flush()
        return complaint
