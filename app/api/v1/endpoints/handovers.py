"""Tovar topshirish (handover) oqimi endpointlari.

Sotuvchi handover yaratadi (kod oladi) -> uchrashuvda kodni xaridorga aytadi ->
xaridor kodni kiritib tasdiqlaydi -> capture (pul sotuvchiga), order COMPLETED.
"""

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.handover import Handover
from app.models.user import User
from app.schemas.handover import HandoverConfirm, HandoverCreate, HandoverRead
from app.services.handover_service import HandoverService

router = APIRouter()


def _to_read(handover: Handover, viewer: User) -> HandoverRead:
    """Handoverni javobga aylantiradi; kod faqat sotuvchi/adminga qoldiriladi."""
    data = HandoverRead.model_validate(handover)
    if not HandoverService.is_code_visible(handover, viewer):
        data.code = None
    return data


@router.post("", response_model=HandoverRead, status_code=status.HTTP_201_CREATED)
def create_handover(
    payload: HandoverCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> HandoverRead:
    handover = HandoverService(db).create_handover(
        order_id=payload.order_id,
        seller=current_user,
        method=payload.method,
        meet_address=payload.meet_address,
    )
    # Sotuvchi yaratdi — kod ko'rsatiladi.
    return _to_read(handover, current_user)


@router.post("/{order_id}/confirm", response_model=HandoverRead)
def confirm_handover(
    order_id: int,
    payload: HandoverConfirm,
    current_user: CurrentUser,
    db: DbSession,
) -> HandoverRead:
    handover = HandoverService(db).confirm_handover(order_id, current_user, payload.code)
    # Xaridor tasdiqladi — u sotuvchi emas, kod yashiriladi.
    return _to_read(handover, current_user)


@router.get("/{order_id}", response_model=HandoverRead)
def read_handover(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> HandoverRead:
    handover = HandoverService(db).get_for_participant(order_id, current_user)
    return _to_read(handover, current_user)
