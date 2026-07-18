from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BidStatus
from app.money.fields import TiyinAmount


class BidCreate(BaseModel):
    # Pul tiyinda, JSON'da string: {"amount": "6500025"} = 65 000.25 so'm
    # amount — hoziroq qo'yiladigan ko'rinadigan bid.
    amount: TiyinAmount = Field(gt=0)
    # max_amount — proxy shift (ixtiyoriy): keyingi raqiblarga qarshi tizim
    # avtomatik ko'taradigan MAKSIMAL summa. Berilmasa proxy o'chiq.
    # Serverga yashirin qoladi — javobda hech qachon qaytmaydi.
    max_amount: TiyinAmount | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_max(self) -> "BidCreate":
        if self.max_amount is not None and self.max_amount < self.amount:
            raise ValueError("max_amount amount'dan kichik bo'lmasligi kerak")
        return self


class BidRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auction_id: int
    bidder_id: int
    amount: TiyinAmount
    status: BidStatus
    created_at: datetime
