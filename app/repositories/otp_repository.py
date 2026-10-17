from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import OtpPurpose
from app.models.otp import OtpCode


class OtpRepository:
    """OTP kodlar jadvaliga kirish — faqat DB o'qish/yozish."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, otp: OtpCode) -> OtpCode:
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
        return otp

    def get_latest(self, phone: str, purpose: OtpPurpose) -> OtpCode | None:
        """Raqam + maqsad bo'yicha eng oxirgi kodni oladi (holatidan qat'i nazar).

        Resend cooldown tekshiruvi uchun — oxirgi yuborilgan kod qachon
        yaratilganini bilish kerak.
        """
        statement = (
            select(OtpCode)
            .where(OtpCode.phone == phone, OtpCode.purpose == purpose)
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def get_latest_active(self, phone: str, purpose: OtpPurpose, now: datetime) -> OtpCode | None:
        """Iste'mol qilinmagan va muddati o'tmagan eng oxirgi kodni oladi.

        Tekshiruvda (`verify_otp`) faqat shu kod hisobga olinadi — eski, muddati
        o'tgan yoki allaqachon ishlatilgan kodlar e'tiborga olinmaydi.
        """
        statement = (
            select(OtpCode)
            .where(
                OtpCode.phone == phone,
                OtpCode.purpose == purpose,
                OtpCode.consumed_at.is_(None),
                OtpCode.expires_at > now,
            )
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def count_since_for_phone(self, phone: str, since: datetime) -> int:
        """`since` dan beri shu raqamga yaratilgan kodlar soni (kunlik limit uchun)."""
        statement = (
            select(func.count())
            .select_from(OtpCode)
            .where(OtpCode.phone == phone, OtpCode.created_at >= since)
        )
        return self.db.scalar(statement) or 0

    def count_since_for_ip(self, ip: str, since: datetime) -> int:
        """`since` dan beri shu IP'dan yaratilgan kodlar soni (kunlik limit uchun)."""
        statement = (
            select(func.count())
            .select_from(OtpCode)
            .where(OtpCode.ip == ip, OtpCode.created_at >= since)
        )
        return self.db.scalar(statement) or 0

    def save(self, otp: OtpCode) -> OtpCode:
        """Mavjud kod holatini saqlaydi (attempts++ yoki consumed_at belgilash)."""
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
        return otp
