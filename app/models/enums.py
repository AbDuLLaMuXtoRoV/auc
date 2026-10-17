from enum import StrEnum


class ItemCondition(StrEnum):
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"


class ItemStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PENDING = "pending"
    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"


class AuctionStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"
    RESERVE_NOT_MET = "reserve_not_met"


class BidStatus(StrEnum):
    VALID = "valid"
    OUTBID = "outbid"
    CANCELLED = "cancelled"
    # Foydalanuvchi qaytarib oldi (typo/xato stavka). Audit logda qoladi.
    RETRACTED = "retracted"
    # Admin bekor qildi (shill/firibgarlik). Joriy narx qayta hisoblanadi.
    INVALIDATED = "invalidated"


class UserRole(StrEnum):
    USER = "user"
    SELLER = "seller"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"  # to'liq huquq: rol berish, adminlarni boshqarish


# Moderatsiya huquqiga ega rollar. Superadmin — adminning USTKI to'plami:
# admin ruxsat etilgan hamma joyda superadmin ham o'tishi shart. Tekshiruvni
# `role == UserRole.ADMIN` deb yozish superadminni jimgina chetlab o'tadi.
ADMIN_ROLES: frozenset[UserRole] = frozenset({UserRole.ADMIN, UserRole.SUPERADMIN})


def is_admin(role: UserRole) -> bool:
    """Rol admin yoki superadminmi — moderatsiya tekshiruvlari uchun yagona manba."""
    return role in ADMIN_ROLES


class HandoverMethod(StrEnum):
    LOCAL_MEETUP = "local_meetup"
    DELIVERY = "delivery"


class HandoverStatus(StrEnum):
    PENDING = "pending"  # sotuvchi yaratdi, kod berildi
    COMPLETED = "completed"  # xaridor kod bilan tasdiqladi -> capture
    FAILED = "failed"


class NotificationType(StrEnum):
    OUTBID = "outbid"  # sizni ortda qoldirishdi
    WON = "won"  # auksionda yutdingiz
    SOLD = "sold"  # lotingiz sotildi
    PAYMENT = "payment"  # to'lov holati
    HANDOVER = "handover"  # topshirish
    DISPUTE = "dispute"
    SECOND_CHANCE = "second_chance"  # rezervga yetmadi — sotuvchiga taklif
    ENDING_SOON = "ending_soon"  # auksion tugashiga oz qoldi


class DisputeReason(StrEnum):
    NOT_RECEIVED = "not_received"  # tovar kelmadi
    NOT_AS_DESCRIBED = "not_as_described"  # ta'rifga mos emas
    DAMAGED = "damaged"  # shikastlangan
    FAKE = "fake"  # soxta
    OTHER = "other"


class DisputeStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED_BUYER = "resolved_buyer"  # xaridor foydasiga (release/refund)
    RESOLVED_SELLER = "resolved_seller"  # sotuvchi foydasiga (capture)


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    # Escrow holatlari (Faza D):
    HELD = "held"  # PSP kartada bloklagan — pul hali ko'chmagan
    RELEASED = "released"  # capture qilindi — sotuvchiga o'tdi
    CANCELLED_HOLD = "cancelled_hold"  # blok bekor qilindi — pul xaridorda qoldi


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PICKUP_PENDING = "pickup_pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ComplaintTargetType(StrEnum):
    ITEM = "item"
    USER = "user"
    AUCTION = "auction"
    MESSAGE = "message"
    ORDER = "order"


class ComplaintStatus(StrEnum):
    OPEN = "open"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ConsentDocumentType(StrEnum):
    """Foydalanuvchi qabul qilishi mumkin bo'lgan huquqiy hujjatlar.

    Nizo chiqqanda "qaysi versiyadagi shartnoma qabul qilingan" savoliga
    javob berish uchun har qabul versiyasi bilan saqlanadi.
    """

    TERMS = "terms"  # foydalanuvchi kelishuvi
    PRIVACY = "privacy"  # maxfiylik siyosati
    AUCTION_RULES = "auction_rules"  # auksion reglamenti
    PUBLIC_OFFER = "public_offer"  # ommaviy oferta (stavka = ofertani qabul)


class OtpPurpose(StrEnum):
    PHONE_VERIFY = "phone_verify"  # telefon raqamni tasdiqlash
    LOGIN = "login"  # OTP orqali kirish
    PASSWORD_RESET = "password_reset"  # parolni tiklash
