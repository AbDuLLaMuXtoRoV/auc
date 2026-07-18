from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AuctionStatus
from app.money import TIYIN_PER_SOUM
from app.money.fields import TiyinAmount


class AuctionCreate(BaseModel):
    item_id: int
    start_time: datetime
    # Auksion tugash vaqtini berishning IKKI yo'li (ayni bittasi majburiy):
    #   1) end_time — aniq sana/vaqt (orqaga moslik uchun saqlangan eski yo'l).
    #   2) duration_days — majburiy deadline (3/5/7 kun), mahsulotning asosiy
    #      qoidasi. Berilsa end_time = start_time + kun sifatida hisoblanadi.
    end_time: datetime | None = None
    duration_days: Literal[3, 5, 7] | None = None
    # Pul tiyinda, JSON'da string: {"minimum_bid_increment": "100000"}
    minimum_bid_increment: TiyinAmount = Field(default=TIYIN_PER_SOUM, gt=0)
    reserve_price: TiyinAmount | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_schedule(self) -> "AuctionCreate":
        # end_time va duration_days'dan AYNAN BITTASI berilishi shart.
        if (self.end_time is None) == (self.duration_days is None):
            raise ValueError("Provide exactly one of end_time or duration_days")

        if self.duration_days is not None:
            # duration_days yo'li: end_time'ni hisoblab qo'yamiz — shunda
            # downstream kod (repo/service) faqat payload.end_time'ni o'qiydi.
            self.end_time = self.start_time + timedelta(days=self.duration_days)
        elif self.end_time <= self.start_time:
            raise ValueError("Auction end time must be after start time")

        return self


class AuctionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    seller_id: int
    start_time: datetime
    end_time: datetime
    duration_days: int | None
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
