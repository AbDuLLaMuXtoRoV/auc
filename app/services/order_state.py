"""Order holati state machine.

`PATCH /orders/{id}/status` ilgari istalgan holatga o'tishga ruxsat berardi
(sotuvchi order'ni PENDING_PAYMENT'dan chiqarib xaridor to'lovini bloklashi
mumkin edi — grifing). Qo'lda status yozish faqat ruxsat etilgan o'tishlar
orqali.
"""

from app.models.enums import OrderStatus

ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING_PAYMENT: frozenset(
        {OrderStatus.PAID, OrderStatus.PICKUP_PENDING, OrderStatus.CANCELLED}
    ),
    OrderStatus.PAID: frozenset(
        {OrderStatus.PICKUP_PENDING, OrderStatus.COMPLETED, OrderStatus.CANCELLED}
    ),
    OrderStatus.PICKUP_PENDING: frozenset({OrderStatus.COMPLETED, OrderStatus.CANCELLED}),
    OrderStatus.COMPLETED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class InvalidOrderTransition(Exception):
    def __init__(self, current: OrderStatus, target: OrderStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Order holati {current.value} -> {target.value} taqiqlangan")


def assert_order_transition(current: OrderStatus, target: OrderStatus) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidOrderTransition(current, target)
