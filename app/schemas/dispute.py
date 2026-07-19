from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DisputeReason, DisputeStatus


class DisputeCreate(BaseModel):
    """Xaridor nizo ochish so'rovi. Payment serverdan (order bo'yicha faol
    HELD hold) topiladi — klientdan payment_id olinmaydi."""

    order_id: int
    reason: DisputeReason
    description: str | None = Field(default=None, max_length=2000)


class DisputeResolve(BaseModel):
    """Admin qarori. decision:
    "buyer"  -> release_hold (blok bekor, pul xaridorda qoladi)
    "seller" -> capture_payment (pul sotuvchiga o'tadi)
    """

    decision: Literal["buyer", "seller"]
    resolution: str = Field(min_length=1, max_length=2000)


class DisputeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    reason: DisputeReason
    status: DisputeStatus
    description: str | None
    resolution: str | None
    resolved_at: datetime | None
    created_at: datetime
