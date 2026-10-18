from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeviceDefect, DeviceGrade
from app.money.fields import TiyinAmount


class DeviceModelBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str


class PriceGuideInfo(BaseModel):
    """Narxlar qanday hisoblangani — UI har doim ko'rsatadi (shaffoflik)."""

    rate_tiyin_per_krw: int
    market_adjust_bps: int
    updated_at: datetime | None
    source: str = "Koreya bozoridagi diler (buy-back) narxlari, so'mga o'girilgan"


class DeviceModelRead(BaseModel):
    id: int
    slug: str
    brand: str
    name: str
    series: str
    storages: list[str]


class PriceGuideIndex(BaseModel):
    info: PriceGuideInfo
    models: list[DeviceModelRead]


class StoragePrices(BaseModel):
    """Bitta xotira hajmi uchun daraja narxlari (tiyin). null — bu darajada baholanmaydi."""

    storage: str
    a: TiyinAmount | None
    a_minus: TiyinAmount | None
    b_plus: TiyinAmount | None
    b_minus: TiyinAmount | None
    base: TiyinAmount | None


class DeviceModelDetail(DeviceModelRead):
    info: PriceGuideInfo
    prices: list[StoragePrices]
    # Nosozlik -> ajratma (tiyin). Ro'yxatda yo'q nosozlik ajratilmaydi.
    deductions: dict[DeviceDefect, TiyinAmount]
    scrap: TiyinAmount | None


class EstimateRequest(BaseModel):
    model_id: int
    storage: str = Field(min_length=2, max_length=10)
    grade: DeviceGrade | None = None
    battery_health: int | None = Field(default=None, ge=1, le=100)
    defects: list[DeviceDefect] = Field(default_factory=list, max_length=len(DeviceDefect))


class EstimateDeduction(BaseModel):
    defect: DeviceDefect
    amount: TiyinAmount


class EstimateRead(BaseModel):
    model_id: int
    model_name: str
    storage: str
    grade: DeviceGrade | None
    # Daraja (va batareya) bo'yicha narx — ajratmalardan OLDIN.
    grade_price: TiyinAmount
    battery_adjusted: bool
    deductions: list[EstimateDeduction]
    # Yakuniy taxminiy baho. Ajratmalar "ehtiyot qism" narxidan pastga tushirmaydi.
    estimate: TiyinAmount
    floored_to_scrap: bool
    info: PriceGuideInfo


class PriceGuideSettingsUpdate(BaseModel):
    # 1 won necha tiyin: 8.55 so'm -> 855. Chegaralar xato kiritishdan himoya.
    rate_tiyin_per_krw: int = Field(ge=1, le=100_000)
    market_adjust_bps: int = Field(ge=-5_000, le=20_000)
