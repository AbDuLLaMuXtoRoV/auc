from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ConsentDocumentType
from app.models.legal_consent import LegalConsent


class LegalConsentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        document_type: ConsentDocumentType,
        version: str,
        ip: str | None,
    ) -> LegalConsent:
        consent = LegalConsent(
            user_id=user_id,
            document_type=document_type,
            version=version,
            ip=ip,
        )
        self.db.add(consent)
        self.db.flush()
        return consent

    def list_by_user(self, user_id: int) -> list[LegalConsent]:
        statement = (
            select(LegalConsent)
            .where(LegalConsent.user_id == user_id)
            .order_by(LegalConsent.accepted_at.desc())
        )
        return list(self.db.scalars(statement))
