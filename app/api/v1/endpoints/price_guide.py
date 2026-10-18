from fastapi import APIRouter, Depends

from app.core.dependencies import DbSession
from app.core.rate_limit import RateLimiter
from app.schemas.price_guide import (
    DeviceModelDetail,
    EstimateRead,
    EstimateRequest,
    PriceGuideIndex,
)
from app.services.price_guide_service import PriceGuideService

router = APIRouter()


@router.get("", response_model=PriceGuideIndex)
def read_price_guide(db: DbSession) -> PriceGuideIndex:
    """Modellar ro'yxati + kurs ma'lumoti (ochiq)."""
    return PriceGuideService(db).index()


@router.get("/models/{slug}", response_model=DeviceModelDetail)
def read_device_model(slug: str, db: DbSession) -> DeviceModelDetail:
    """Model: xotira x daraja narxlari va nosozlik ajratmalari (so'mda)."""
    return PriceGuideService(db).model_detail(slug)


@router.post(
    "/estimate",
    response_model=EstimateRead,
    dependencies=[Depends(RateLimiter("bid", 60))],
)
def estimate_device(payload: EstimateRequest, db: DbSession) -> EstimateRead:
    """Telefon holati bo'yicha taxminiy baho (ochiq, kirish shart emas)."""
    return PriceGuideService(db).estimate(payload)
