from fastapi import APIRouter

from app.core.dependencies import CurrentActiveUser, CurrentAdminUser, DbSession
from app.models.order import Order
from app.schemas.order import OrderRead, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter()


@router.get("/buyer", response_model=list[OrderRead])
def read_buyer_orders(current_user: CurrentActiveUser, db: DbSession) -> list[Order]:
    return OrderService(db).list_buyer_orders(current_user)


@router.get("/seller", response_model=list[OrderRead])
def read_seller_orders(current_user: CurrentActiveUser, db: DbSession) -> list[Order]:
    return OrderService(db).list_seller_orders(current_user)


@router.get("/admin", response_model=list[OrderRead])
def read_admin_orders(current_user: CurrentAdminUser, db: DbSession) -> list[Order]:
    return OrderService(db).list_admin_orders(current_user)


@router.get("/{order_id}", response_model=OrderRead)
def read_order(order_id: int, current_user: CurrentActiveUser, db: DbSession) -> Order:
    return OrderService(db).get_order_for_user(order_id, current_user)


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    current_user: CurrentActiveUser,
    db: DbSession,
) -> Order:
    return OrderService(db).update_order_status(order_id, payload.status, current_user)
