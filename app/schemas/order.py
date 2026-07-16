from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import OrderStatus
from app.money.fields import TiyinAmount


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auction_id: int
    item_id: int
    buyer_id: int
    seller_id: int
    final_price: TiyinAmount
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
