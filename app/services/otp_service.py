"""OTP (bir martalik kod) biznes mantiqi — telefon tasdiqlash / SMS.

Xavfsizlik tamoyillari:
  - Xom kod DBda saqlanmaydi — faqat HMAC-SHA256 hash (`settings.secret_key`).
  - Solishtirish `hmac.compare_digest` bilan (timing-safe).
  - Kod `secrets` moduli orqali generatsiya qilinadi (kriptografik tasodifiy).
  - Cheklovlar: resend cooldown, kunlik raqam/IP limitlari, urinishlar soni —
    SMS bombing va brute-force himoyasi.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import OtpPurpose
from app.models.otp import OtpCode
from app.repositories.otp_repository import OtpRepository
from app.services.sms_provider import get_sms_provider

_DIGITS = "0123456789"


def _hash_code(code: str) -> str:
    """Kodni HMAC-SHA256 bilan hash qiladi (kalit — settings.secret_key).

    HMAC (oddiy sha256 emas): kalitsiz hujumchi lug'at (rainbow table) bilan
    6 xonali kodni oldindan hisoblab qo'ya olmasligi uchun.
    """
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _generate_code(length: int) -> str:
    """`length` xonali tasodifiy raqamli kod (yetakchi nol saqlanadi)."""
    return "".join(secrets.choice(_DIGITS) for _ in range(length))


class OtpService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.otps = OtpRepository(db)

    def request_otp(
        self,
        phone: str,
        purpose: OtpPurpose,
        ip: str | None = None,
    ) -> tuple[OtpCode, str]:
        """Yangi OTP kod generatsiya qiladi, hash qilib saqlaydi va SMS yuboradi.

        Xom kodni HAM qaytaradi (`(OtpCode, code)`) — u DBda saqlanmagani uchun
        boshqa yo'l bilan olib bo'lmaydi. Chaqiruvchi (endpoint) uni faqat
        non-prod muhitda javobda oshkor qiladi; prod'da kod faqat SMS orqali ketadi.

        Cheklovlar (buzilsa aniq xato):
          - OTP o'chirilgan bo'lsa (`otp_enabled=False`) — 503.
          - Resend cooldown ichida qayta so'ralsa — 429.
          - Kunlik raqam yoki IP limiti oshsa — 429.
        """
        if not settings.otp_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OTP tasdiqlash vaqtincha o'chirilgan",
            )

        now = datetime.now(UTC)
        self._enforce_cooldown(phone, purpose, now)
        self._enforce_daily_limits(phone, ip, now)

        code = _generate_code(settings.otp_code_length)
        otp = OtpCode(
            phone=phone,
            code_hash=_hash_code(code),
            purpose=purpose,
            expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
            ip=ip,
        )
        self.otps.create(otp)

        # SMS yuborish so'rovni bloklamasligi kerak, lekin log provayderda bu
        # arzon. Real provayderda bu keyin fon vazifasiga ko'chiriladi (TODO).
        minutes = settings.otp_ttl_seconds // 60
        text = f"Bazart tasdiqlash kodi: {code}. Amal qilish muddati: {minutes} daqiqa."
        get_sms_provider().send(phone, text)
        return otp, code

    def verify_otp(self, phone: str, code: str, purpose: OtpPurpose) -> OtpCode:
        """Kodni tekshiradi; to'g'ri bo'lsa iste'mol qilingan deb belgilaydi.

        - Faol (muddati o'tmagan, ishlatilmagan) kod bo'lmasa — 400.
        - Urinishlar `otp_max_attempts` ga yetgan bo'lsa — 429 (bloklangan).
        - Kod noto'g'ri — `attempts += 1`, 400.
        - Kod to'g'ri — `consumed_at` belgilanadi, kod qaytariladi.
        """
        now = datetime.now(UTC)
        otp = self.otps.get_latest_active(phone, purpose, now)
        if otp is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kod topilmadi yoki muddati o'tgan",
            )

        if otp.attempts >= settings.otp_max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Juda ko'p noto'g'ri urinish. Yangi kod so'rang.",
            )

        if not hmac.compare_digest(otp.code_hash, _hash_code(code)):
            otp.attempts += 1
            self.otps.save(otp)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Noto'g'ri kod",
            )

        otp.consumed_at = now
        self.otps.save(otp)
        return otp

    def _enforce_cooldown(self, phone: str, purpose: OtpPurpose, now: datetime) -> None:
        """Oxirgi kod juda yaqinda yuborilgan bo'lsa qayta yuborishni bloklaydi."""
        cooldown = settings.otp_resend_cooldown_seconds
        if cooldown <= 0:
            return
        last = self.otps.get_latest(phone, purpose)
        if last is not None:
            elapsed = (now - last.created_at).total_seconds()
            if elapsed < cooldown:
                retry_after = int(cooldown - elapsed) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Yangi kod so'rashdan oldin {retry_after} soniya kuting",
                    headers={"Retry-After": str(retry_after)},
                )

    def _enforce_daily_limits(self, phone: str, ip: str | None, now: datetime) -> None:
        """Kuniga bir raqam va bir IP uchun kodlar sonini cheklaydi (SMS bombing)."""
        day_ago = now - timedelta(days=1)

        phone_count = self.otps.count_since_for_phone(phone, day_ago)
        if phone_count >= settings.otp_daily_limit_per_phone:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bu raqam uchun kunlik kod limiti tugadi",
            )

        if ip is not None:
            ip_count = self.otps.count_since_for_ip(ip, day_ago)
            if ip_count >= settings.otp_daily_limit_per_ip:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Bu IP uchun kunlik kod limiti tugadi",
                )
