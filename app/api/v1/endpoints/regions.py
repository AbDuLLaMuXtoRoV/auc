from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession
from app.models.region import District, Region
from app.repositories.region_repository import RegionRepository
from app.schemas.region import DistrictRead, RegionRead

router = APIRouter()


@router.get("", response_model=list[RegionRead])
def list_regions(db: DbSession) -> list[Region]:
    """Barcha hududlar (viloyatlar). Ochiq — auth talab qilinmaydi."""
    return RegionRepository(db).list_regions()


@router.get("/{region_id}/districts", response_model=list[DistrictRead])
def list_districts(region_id: int, db: DbSession) -> list[District]:
    """Hudud ichidagi tumanlar. Hudud yo'q bo'lsa 404."""
    repo = RegionRepository(db)
    if repo.get_region(region_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")
    return repo.list_districts(region_id)
