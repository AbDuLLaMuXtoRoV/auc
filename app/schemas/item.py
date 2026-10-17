from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import ItemCondition, ItemStatus
from app.money.fields import TiyinAmount


class ItemImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    image_url: str
    is_primary: bool
    created_at: datetime


class ItemCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    category_id: int | None = None
    images: list[str] = Field(default_factory=list, max_length=20)
    condition: ItemCondition = ItemCondition.USED
    location: str | None = Field(default=None, max_length=160)
    item_location: str | None = Field(default=None, max_length=160)
    # Domen boyitish.
    year: int | None = Field(default=None, ge=1900, le=2100)
    equipment: str | None = Field(default=None, max_length=2000)
    # Nuqsonlar — xaridor tovar holatini oldindan bilishi uchun tavsiya etiladi.
    # MVP'da ixtiyoriy (majburiy qilish — keyingi item-validatsiya bosqichida);
    # maydon mavjud, saqlanadi va qidiruvga kiradi.
    defects: str | None = Field(default=None, max_length=2000)
    video_url: str | None = Field(default=None, max_length=500)
    region_id: int | None = None
    district_id: int | None = None
    # Pul tiyinda, JSON'da string: {"starting_price": "6200050"}
    starting_price: TiyinAmount = Field(gt=0)
    reserve_price: TiyinAmount | None = Field(default=None, gt=0)


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    category_id: int | None = None
    images: list[str] | None = Field(default=None, max_length=20)
    condition: ItemCondition | None = None
    status: ItemStatus | None = None
    location: str | None = Field(default=None, max_length=160)
    item_location: str | None = Field(default=None, max_length=160)
    year: int | None = Field(default=None, ge=1900, le=2100)
    equipment: str | None = Field(default=None, max_length=2000)
    defects: str | None = Field(default=None, min_length=1, max_length=2000)
    video_url: str | None = Field(default=None, max_length=500)
    region_id: int | None = None
    district_id: int | None = None
    starting_price: TiyinAmount | None = Field(default=None, gt=0)
    reserve_price: TiyinAmount | None = Field(default=None, gt=0)


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    title: str
    description: str | None
    category_id: int | None
    images: list[str]
    condition: ItemCondition
    status: ItemStatus
    location: str | None
    item_location: str | None
    year: int | None
    equipment: str | None
    defects: str | None
    video_url: str | None
    region_id: int | None
    district_id: int | None
    view_count: int
    published_at: datetime | None
    starting_price: TiyinAmount
    # DIQQAT: reserve_price ATAYLAB javob JSON'iga chiqmaydi (exclude=True) —
    # u sotuvchining maxfiy minimal narxi. Oshkor qilinsa auksion strategiyasi
    # buziladi. Faqat rezerv BORLIGI has_reserve orqali bildiriladi.
    reserve_price: TiyinAmount | None = Field(default=None, exclude=True)
    item_images: list[ItemImageRead] = Field(default_factory=list)
    # Qayta joylangan e'lon bo'lsa — asl (sotilmagan) e'lon id'si.
    relisted_from_id: int | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_reserve(self) -> bool:
        """Lotda maxfiy rezerv narx bor-yo'qligi (qiymatni oshkor qilmay)."""
        return self.reserve_price is not None


class ItemImageUploadRead(BaseModel):
    image: ItemImageRead
