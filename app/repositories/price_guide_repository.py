from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.price_guide import DeviceModel, DevicePrice, PriceGuideSettings

SETTINGS_ID = 1


class PriceGuideRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_models(self) -> list[DeviceModel]:
        statement = (
            select(DeviceModel)
            .options(selectinload(DeviceModel.prices))
            .order_by(DeviceModel.sort_order, DeviceModel.id)
        )
        return list(self.db.scalars(statement))

    def get_model(self, model_id: int) -> DeviceModel | None:
        return self.db.get(DeviceModel, model_id)

    def get_model_by_slug(self, slug: str) -> DeviceModel | None:
        statement = (
            select(DeviceModel)
            .where(DeviceModel.slug == slug)
            .options(selectinload(DeviceModel.prices))
        )
        return self.db.scalar(statement)

    def get_price(self, model_id: int, storage: str) -> DevicePrice | None:
        statement = select(DevicePrice).where(
            DevicePrice.model_id == model_id, DevicePrice.storage == storage
        )
        return self.db.scalar(statement)

    def get_settings(self) -> PriceGuideSettings | None:
        return self.db.get(PriceGuideSettings, SETTINGS_ID)

    def save_settings(
        self, *, rate_tiyin_per_krw: int, market_adjust_bps: int, updated_by_id: int | None
    ) -> PriceGuideSettings:
        settings_row = self.get_settings()
        if settings_row is None:
            settings_row = PriceGuideSettings(id=SETTINGS_ID)
        settings_row.rate_tiyin_per_krw = rate_tiyin_per_krw
        settings_row.market_adjust_bps = market_adjust_bps
        settings_row.updated_by_id = updated_by_id
        self.db.add(settings_row)
        self.db.commit()
        self.db.refresh(settings_row)
        return settings_row
