from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentStatus
from app.money.fields import TiyinAmount


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
    # Pul tiyinda, JSON'da string
    amount: TiyinAmount = Field(gt=0)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    provider: str = Field(default="mock", min_length=2, max_length=80)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    buyer_id: int
    amount: TiyinAmount
    currency: str
    status: PaymentStatus
    provider: str
    provider_payment_id: str | None
    created_at: datetime
    updated_at: datetime
