from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.payment import Payment, PaymentMethod
from app.schemas.payment import (
    PaymentIntentCreate,
    PaymentMethodCreate,
    PaymentMethodRead,
    PaymentRead,
)
from app.services.payment_service import PaymentService

router = APIRouter()


@router.post("/methods", response_model=PaymentMethodRead, status_code=status.HTTP_201_CREATED)
def create_method(
    payload: PaymentMethodCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PaymentMethod:
    payment_method = PaymentMethod(user_id=current_user.id, **payload.model_dump())
    db.add(payment_method)
    db.commit()
    db.refresh(payment_method)
    return payment_method


@router.get("/methods", response_model=list[PaymentMethodRead])
def read_methods(current_user: CurrentUser, db: DbSession) -> list[PaymentMethod]:
    statement = select(PaymentMethod).where(PaymentMethod.user_id == current_user.id)
    return list(db.scalars(statement))


@router.post("/intents", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment_intent(
    payload: PaymentIntentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Payment:
    return PaymentService(db).create_payment_intent(payload, current_user)


@router.post("/{payment_id}/confirm-mock", response_model=PaymentRead)
def confirm_mock_payment(
    payment_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Payment:
    return PaymentService(db).confirm_mock_payment(payment_id, current_user)


@router.get("/orders/{order_id}", response_model=PaymentRead)
def get_payment_by_order(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Payment:
    return PaymentService(db).get_payment_by_order(order_id, current_user)
