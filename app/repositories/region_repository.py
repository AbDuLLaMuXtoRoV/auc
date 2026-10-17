from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.region import District, Region


class RegionRepository:
    """Hudud va tuman ma'lumotlariga kirish (asosan o'qish — statik ma'lumot)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_regions(self) -> list[Region]:
        statement = select(Region).order_by(Region.name_uz.asc())
        return list(self.db.scalars(statement))

    def get_region(self, region_id: int) -> Region | None:
        return self.db.get(Region, region_id)

    def get_district(self, district_id: int) -> District | None:
        return self.db.get(District, district_id)

    def list_districts(self, region_id: int) -> list[District]:
        statement = (
            select(District).where(District.region_id == region_id).order_by(District.name_uz.asc())
        )
        return list(self.db.scalars(statement))

    def get_by_code(self, code: str) -> Region | None:
        statement = select(Region).where(Region.code == code)
        return self.db.scalar(statement)
