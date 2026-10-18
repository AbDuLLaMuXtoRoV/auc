"""Telefon narx ko'rsatkichi: model narxlari va taxminiy baho hisobi.

Manba — Koreya diler (buy-back) narxlari (won). Hisob butunlay won'da, butun
sonlarda olib boriladi va faqat oxirida bitta joyda so'mga o'giriladi
(`convert_foreign_to_tiyin`): kurs + bozor tuzatmasi admin sozlamasidan.

Baho qoidalari (manba jadval izohlari bo'yicha):
1. Daraja narxi (A / A- / B+ / B-). Daraja berilmasa yoki shu darajada
   sotib olinmasa ("X") — holatidan qat'i nazar narx (base).
2. Batareya darajaning me'yoridan past bo'lsa (A/A- < 90%, B+ < 85%, B- < 81%):
   jadvalda "batareya past" narxi bo'lsa — o'sha, bo'lmasa bir daraja past narx.
3. Har nosozlik uchun model ajratmasi ayiriladi.
4. Natija "ehtiyot qism" (scrap) narxidan pastga tushmaydi.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import DeviceDefect, DeviceGrade
from app.models.price_guide import DeviceModel, DevicePrice
from app.models.user import User
from app.money import Tiyin, convert_foreign_to_tiyin
from app.repositories.price_guide_repository import PriceGuideRepository
from app.schemas.price_guide import (
    DeviceModelDetail,
    DeviceModelRead,
    EstimateDeduction,
    EstimateRead,
    EstimateRequest,
    PriceGuideIndex,
    PriceGuideInfo,
    PriceGuideSettingsUpdate,
    StoragePrices,
)

GRADE_ORDER = (DeviceGrade.A, DeviceGrade.A_MINUS, DeviceGrade.B_PLUS, DeviceGrade.B_MINUS)

# Daraja uchun minimal batareya holati (%) — manba jadval mezonlari.
BATTERY_MIN = {
    DeviceGrade.A: 90,
    DeviceGrade.A_MINUS: 90,
    DeviceGrade.B_PLUS: 85,
    DeviceGrade.B_MINUS: 81,
}

_GRADE_COLUMN = {
    DeviceGrade.A: "grade_a_krw",
    DeviceGrade.A_MINUS: "grade_a_minus_krw",
    DeviceGrade.B_PLUS: "grade_b_plus_krw",
    DeviceGrade.B_MINUS: "grade_b_minus_krw",
}
_BATTERY_LOW_COLUMN = {
    DeviceGrade.A: "battery_low_a_krw",
    DeviceGrade.A_MINUS: "battery_low_a_krw",
    DeviceGrade.B_PLUS: "battery_low_b_plus_krw",
}
_DEFECT_COLUMN = {defect: f"{defect.value}_krw" for defect in DeviceDefect}


class PriceGuideService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PriceGuideRepository(db)

    # --- Sozlama va o'girish --------------------------------------------

    def info(self) -> PriceGuideInfo:
        row = self.repo.get_settings()
        if row is None:
            return PriceGuideInfo(
                rate_tiyin_per_krw=settings.price_guide_default_rate_tiyin_per_krw,
                market_adjust_bps=settings.price_guide_default_market_adjust_bps,
                updated_at=None,
            )
        return PriceGuideInfo(
            rate_tiyin_per_krw=row.rate_tiyin_per_krw,
            market_adjust_bps=row.market_adjust_bps,
            updated_at=row.updated_at,
        )

    def update_settings(self, admin: User, payload: PriceGuideSettingsUpdate) -> PriceGuideInfo:
        self.repo.save_settings(
            rate_tiyin_per_krw=payload.rate_tiyin_per_krw,
            market_adjust_bps=payload.market_adjust_bps,
            updated_by_id=admin.id,
        )
        return self.info()

    @staticmethod
    def _to_tiyin(info: PriceGuideInfo, krw: int | None) -> Tiyin | None:
        if krw is None:
            return None
        return convert_foreign_to_tiyin(krw, info.rate_tiyin_per_krw, info.market_adjust_bps)

    # --- Ro'yxat va model ------------------------------------------------

    def index(self) -> PriceGuideIndex:
        return PriceGuideIndex(
            info=self.info(), models=[_model_read(m) for m in self.repo.list_models()]
        )

    def model_detail(self, slug: str) -> DeviceModelDetail:
        model = self.repo.get_model_by_slug(slug)
        if model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
        info = self.info()
        deductions = {}
        for defect, column in _DEFECT_COLUMN.items():
            amount = self._to_tiyin(info, getattr(model, column))
            if amount:
                deductions[defect] = amount
        return DeviceModelDetail(
            **_model_read(model).model_dump(),
            info=info,
            prices=[
                StoragePrices(
                    storage=p.storage,
                    a=self._to_tiyin(info, p.grade_a_krw),
                    a_minus=self._to_tiyin(info, p.grade_a_minus_krw),
                    b_plus=self._to_tiyin(info, p.grade_b_plus_krw),
                    b_minus=self._to_tiyin(info, p.grade_b_minus_krw),
                    base=self._to_tiyin(info, p.base_krw),
                )
                for p in model.prices
            ],
            deductions=deductions,
            scrap=self._to_tiyin(info, model.scrap_krw),
        )

    def validate_device(self, model_id: int | None, storage: str | None) -> None:
        """E'londagi telefon maydonlari: model mavjud va xotira shu modelda bor (400)."""
        if model_id is None:
            if storage is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="device_storage requires device_model_id",
                )
            return
        if self.repo.get_model(model_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown device model"
            )
        if storage is not None and self.repo.get_price(model_id, storage) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage is not available for this model",
            )

    # --- Taxminiy baho -----------------------------------------------------

    def estimate(self, payload: EstimateRequest) -> EstimateRead:
        model = self.repo.get_model(payload.model_id)
        if model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
        row = self.repo.get_price(model.id, payload.storage)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage is not available for this model",
            )

        grade_krw, battery_adjusted = _grade_price_krw(row, payload.grade, payload.battery_health)
        if grade_krw is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No price for this configuration"
            )

        defects = list(dict.fromkeys(payload.defects))  # tartibni saqlab, takrorsiz
        deductions_krw = [(d, getattr(model, _DEFECT_COLUMN[d]) or 0) for d in defects]
        total_krw = grade_krw - sum(amount for _, amount in deductions_krw)
        floor_krw = model.scrap_krw or 0
        floored = total_krw < floor_krw
        total_krw = max(total_krw, floor_krw)

        info = self.info()
        return EstimateRead(
            model_id=model.id,
            model_name=model.name,
            storage=row.storage,
            grade=payload.grade,
            grade_price=self._to_tiyin(info, grade_krw),
            battery_adjusted=battery_adjusted,
            deductions=[
                EstimateDeduction(defect=d, amount=self._to_tiyin(info, amount))
                for d, amount in deductions_krw
                if amount
            ],
            estimate=self._to_tiyin(info, total_krw),
            floored_to_scrap=floored,
            info=info,
        )


def _model_read(model: DeviceModel) -> DeviceModelRead:
    return DeviceModelRead(
        id=model.id,
        slug=model.slug,
        brand=model.brand,
        name=model.name,
        series=model.series,
        storages=[p.storage for p in model.prices],
    )


def _grade_price_krw(
    row: DevicePrice, grade: DeviceGrade | None, battery: int | None
) -> tuple[int | None, bool]:
    """Daraja + batareya bo'yicha narx (won) va batareya hisobga olinganmi."""
    if grade is None:
        return row.base_krw, False

    price = getattr(row, _GRADE_COLUMN[grade])
    if battery is None or battery >= BATTERY_MIN[grade]:
        return (price if price is not None else row.base_krw), False

    low_column = _BATTERY_LOW_COLUMN.get(grade)
    low_price = getattr(row, low_column) if low_column else None
    if low_price is not None:
        return low_price, True
    # Jadvalda "batareya past" narxi yo'q — bir daraja past narx (u ham yo'q bo'lsa base).
    for lower in GRADE_ORDER[GRADE_ORDER.index(grade) + 1 :]:
        lower_price = getattr(row, _GRADE_COLUMN[lower])
        if lower_price is not None:
            return lower_price, True
    return row.base_krw, True
