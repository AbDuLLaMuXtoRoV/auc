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


class UserRole(StrEnum):
    USER = "user"
    SELLER = "seller"
    ADMIN = "admin"


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
