from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.dispute import Dispute
from app.schemas.dispute import DisputeCreate, DisputeRead, DisputeResolve
from app.services.dispute_service import DisputeService

router = APIRouter()


@router.post("", response_model=DisputeRead, status_code=status.HTTP_201_CREATED)
def open_dispute(
    payload: DisputeCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Dispute:
    """Xaridor HELD hold ustidan nizo ochadi."""
    return DisputeService(db).open_dispute(
        payload.order_id, current_user, payload.reason, payload.description
    )


@router.get("", response_model=list[DisputeRead])
def list_disputes(
    current_user: CurrentUser,
    db: DbSession,
    dispute_status: str | None = Query(default=None, alias="status"),
) -> list[Dispute]:
    """Menikilar. Admin `?status=open` bilan ochiq nizolar navbatini oladi."""
    service = DisputeService(db)
    if dispute_status == "open":
        return service.list_open_for_admin(current_user)
    return service.list_mine(current_user)


@router.get("/{dispute_id}", response_model=DisputeRead)
def get_dispute(
    dispute_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Dispute:
    return DisputeService(db).get_for_user(dispute_id, current_user)


@router.post("/{dispute_id}/resolve", response_model=DisputeRead)
def resolve_dispute(
    dispute_id: int,
    payload: DisputeResolve,
    current_user: CurrentUser,
    db: DbSession,
) -> Dispute:
    """Admin nizoni hal qiladi: buyer -> release, seller -> capture."""
    return DisputeService(db).resolve(
        dispute_id, current_user, payload.decision, payload.resolution
    )
