from datetime import UTC, datetime

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ConsentDocumentType


class LegalConsent(Base):
    """Foydalanuvchining huquqiy hujjatga rozilik yozuvi.

    Nizo yoki tekshiruvda "qaysi versiyadagi shartnoma, qachon, qaysi IP'dan
    qabul qilingan" savoliga javob berish uchun har rozilik alohida qator
    sifatida saqlanadi (yangilanmaydi — audit izi). `version` — hujjat matni
    versiyasi; yangi versiya chiqsa yangi qator qo'shiladi.
    """

    __tablename__ = "legal_consents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    document_type: Mapped[ConsentDocumentType] = mapped_column(
        SqlEnum(ConsentDocumentType, name="consent_document_type"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    # IP — INET emas, String: TestClient "testclient" host beradi, INET buni
    # rad etardi. Audit uchun matn saqlash yetarli.
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
