from pydantic import BaseModel, ConfigDict


class RegionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_uz: str
    name_ru: str
    code: str


class DistrictRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    region_id: int
    name_uz: str
    name_ru: str
