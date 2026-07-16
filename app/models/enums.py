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


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PICKUP_PENDING = "pickup_pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
