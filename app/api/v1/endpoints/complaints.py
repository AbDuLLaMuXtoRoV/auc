from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentAdmin, CurrentUser, DbSession
from app.models.complaint import Complaint
from app.models.enums import ComplaintStatus
from app.schemas.complaint import ComplaintCreate, ComplaintRead, ComplaintUpdate
from app.services.complaint_service import ComplaintService

router = APIRouter()


@router.post("", response_model=ComplaintRead, status_code=status.HTTP_201_CREATED)
def create_complaint(
    payload: ComplaintCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Complaint:
    """Shikoyat yaratish (auth). Target polimorfik: item/user/auction/..."""
    return ComplaintService(db).create(
        current_user,
        payload.target_type,
        payload.target_id,
        payload.reason,
        payload.description,
    )


@router.get("", response_model=list[ComplaintRead])
def list_complaints(
    admin: CurrentAdmin,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[Complaint]:
    """Shikoyatlar ro'yxati — faqat admin. `?status=open` bilan filtrlanadi."""
    parsed: ComplaintStatus | None = None
    if status_filter is not None:
        try:
            parsed = ComplaintStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status"
            ) from exc
    return ComplaintService(db).list_for_admin(admin, parsed)


@router.patch("/{complaint_id}", response_model=ComplaintRead)
def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    admin: CurrentAdmin,
    db: DbSession,
) -> Complaint:
    """Shikoyat holatini o'zgartirish — faqat admin. RESOLVED/REJECTED bo'lsa
    resolved_by/resolved_at avtomatik yoziladi."""
    return ComplaintService(db).update_status(complaint_id, admin, payload.status)
