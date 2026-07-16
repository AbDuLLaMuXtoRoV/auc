from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AuctionStatus


class AuctionCreate(BaseModel):
    item_id: int
    start_time: datetime
    end_time: datetime
    minimum_bid_increment: Decimal = Field(default=1, gt=0, max_digits=12, decimal_places=2)
    reserve_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

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
    starting_price: Decimal
    current_price: Decimal
    minimum_bid_increment: Decimal
    reserve_price: Decimal | None
    highest_bidder_id: int | None
    winner_id: int | None
    winning_bid_id: int | None
    created_at: datetime
    updated_at: datetime


class AuctionStatusUpdate(BaseModel):
    status: AuctionStatus = Field(
        description="Initial skeleton supports lifecycle transitions, not automatic settlement yet."
    )
