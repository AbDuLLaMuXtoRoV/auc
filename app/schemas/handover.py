from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import HandoverMethod, HandoverStatus


class HandoverCreate(BaseModel):
    """Sotuvchi tovar topshirishni boshlaydi."""

    order_id: int
    method: HandoverMethod = HandoverMethod.LOCAL_MEETUP
    meet_address: str | None = Field(default=None, max_length=255)


class HandoverConfirm(BaseModel):
    """Xaridor uchrashuvda olgan kodni kiritadi."""

    code: str = Field(min_length=1, max_length=16)


class HandoverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    method: HandoverMethod
    status: HandoverStatus
    meet_address: str | None
    confirmed_at: datetime | None
    created_at: datetime
    # Kod = egalik dalili. Faqat sotuvchiga ko'rsatiladi; xaridor uchun None.
    code: str | None = None
