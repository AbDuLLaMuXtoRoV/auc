from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BidStatus
from app.money.fields import TiyinAmount


def mask_name(full_name: str | None) -> str:
    """To'liq ismni maskalaydi: "Alisher Karimov" -> "A***v".

    Maxfiylik: bid tarixida boshqa foydalanuvchilarga to'liq ism oshkor
    bo'lmaydi (targetlangan aloqa / ijtimoiy muhandislikning oldini olish).
    Bo'sh ism -> "Anonim". Bir harfli ism -> "A*".
    """
    if not full_name or not full_name.strip():
        return "Anonim"
    name = full_name.strip()
    if len(name) == 1:
        return f"{name}*"
    if len(name) == 2:
        return f"{name[0]}*"
    return f"{name[0]}***{name[-1]}"


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
    # Bid tarixida ko'rsatiladigan maskalangan ism (to'liq ism oshkor bo'lmaydi).
    bidder_display: str = "Anonim"
    # Xato stavka belgisi: bid joriy narxdan bir necha barobar yuqori bo'lsa True.
    # Frontend tasdiq oynasi uchun; bidni BLOKLAMAYDI.
    high_bid_warning: bool = False

    @model_validator(mode="before")
    @classmethod
    def _from_orm(cls, data: Any) -> Any:
        """ORM Bid'dan bidder ismini maskalab bidder_display'ga joylaydi.

        `mode="before"` — from_attributes o'qishidan OLDIN ishlaydi, shu sabab
        bid.bidder munosabatidan to'liq ismni olib maskalash imkoni bor.
        dict berilsa (test/ichki) — o'zgarishsiz qaytaramiz.
        """
        if isinstance(data, dict):
            return data
        bidder = getattr(data, "bidder", None)
        return {
            "id": data.id,
            "auction_id": data.auction_id,
            "bidder_id": data.bidder_id,
            "amount": data.amount,
            "status": data.status,
            "created_at": data.created_at,
            "bidder_display": mask_name(getattr(bidder, "full_name", None)),
            "high_bid_warning": getattr(data, "high_bid_warning", False),
        }


class BidInvalidate(BaseModel):
    # Admin bidni bekor qilganda majburiy sabab (audit izi: retract_reason).
    reason: str = Field(min_length=1, max_length=500)
