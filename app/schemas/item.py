from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
    starting_price: TiyinAmount
    reserve_price: TiyinAmount | None
    item_images: list[ItemImageRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ItemImageUploadRead(BaseModel):
    image: ItemImageRead
