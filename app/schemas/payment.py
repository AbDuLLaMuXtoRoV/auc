from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentStatus


class PaymentMethodCreate(BaseModel):
    provider: str = Field(min_length=2, max_length=80)
    label: str | None = Field(default=None, max_length=120)
    token_reference: str | None = Field(default=None, max_length=255)
    is_default: bool = False


class PaymentMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    provider: str
    label: str | None
    is_default: bool
    created_at: datetime


class PaymentIntentCreate(BaseModel):
    order_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    provider: str = Field(default="mock", min_length=2, max_length=80)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    buyer_id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str
    provider_payment_id: str | None
    created_at: datetime
    updated_at: datetime
