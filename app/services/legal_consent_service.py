from sqlalchemy.orm import Session

from app.models.enums import ConsentDocumentType
from app.models.legal_consent import LegalConsent
from app.models.user import User
from app.repositories.legal_consent_repository import LegalConsentRepository


class LegalConsentService:
    """Huquqiy rozilikni yozib qo'yish va foydalanuvchi rozilarini ro'yxatlash.

    Har rozilik yangi qator — o'zgartirilmaydi (audit izi). Nizoda "qaysi
    versiya, qachon, qaysi IP" savoliga javob shu jadvaldan olinadi.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.consents = LegalConsentRepository(db)

    def record(
        self,
        user: User,
        document_type: ConsentDocumentType,
        version: str,
        ip: str | None,
    ) -> LegalConsent:
        consent = self.consents.create(
            user_id=user.id,
            document_type=document_type,
            version=version,
            ip=ip,
        )
        self.db.commit()
        self.db.refresh(consent)
        return consent

    def list_mine(self, user: User) -> list[LegalConsent]:
        return self.consents.list_by_user(user.id)
