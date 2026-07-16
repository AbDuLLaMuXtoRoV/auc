from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BidStatus
from app.money.fields import TiyinAmount


class BidCreate(BaseModel):
    # Pul tiyinda, JSON'da string: {"amount": "6500025"} = 65 000.25 so'm
    amount: TiyinAmount = Field(gt=0)


class BidRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auction_id: int
    bidder_id: int
    amount: TiyinAmount
    status: BidStatus
    created_at: datetime
