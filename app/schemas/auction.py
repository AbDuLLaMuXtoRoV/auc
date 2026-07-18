from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AuctionStatus
from app.money import TIYIN_PER_SOUM
from app.money.fields import TiyinAmount


class AuctionCreate(BaseModel):
    item_id: int
    start_time: datetime
    end_time: datetime
    # Pul tiyinda, JSON'da string: {"minimum_bid_increment": "100000"}
    minimum_bid_increment: TiyinAmount = Field(default=TIYIN_PER_SOUM, gt=0)
    reserve_price: TiyinAmount | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_schedule(self) -> "AuctionCreate":
        if self.end_time <= self.start_time:
            raise ValueError("Auction end time must be after start time")
        return self


class AuctionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    seller_id: int
    start_time: datetime
    end_time: datetime
    status: AuctionStatus
    starting_price: TiyinAmount
    current_price: TiyinAmount
    minimum_bid_increment: TiyinAmount
    reserve_price: TiyinAmount | None
    highest_bidder_id: int | None
    winner_id: int | None
    winning_bid_id: int | None
    created_at: datetime
    updated_at: datetime


class AuctionStatusUpdate(BaseModel):
    # Sotuvchi qo'lda faqat bekor qila oladi (cancelled). ENDED/RESERVE_NOT_MET
    # faqat close oqimi orqali. Batafsil: app/services/auction_state.py
    status: AuctionStatus = Field(description="Sotuvchi so'raydigan holat (amalda: cancelled)")
