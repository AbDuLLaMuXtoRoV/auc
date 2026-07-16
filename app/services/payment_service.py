from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import OrderStatus, PaymentStatus, UserRole
from app.models.payment import Payment
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentIntentCreate
from app.services.payment_providers import get_payment_provider


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.payments = PaymentRepository(db)

    def create_payment_intent(self, payload: PaymentIntentCreate, buyer: User) -> Payment:
        order = self.orders.get(payload.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.buyer_id != buyer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
        if payload.amount != order.final_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount must match order final price",
            )
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order is not pending payment",
            )

        provider = get_payment_provider(payload.provider)
        provider_result = provider.create_payment(amount=payload.amount, currency=payload.currency)
        payment = self.payments.create(
            order_id=order.id,
            buyer_id=buyer.id,
            amount=payload.amount,
            currency=payload.currency,
            provider=provider.provider_name,
            provider_payment_id=provider_result.provider_payment_id,
        )
        payment.status = provider_result.status
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def confirm_mock_payment(self, payment_id: int, actor: User) -> Payment:
        payment = self.payments.get(payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if actor.id != payment.buyer_id and actor.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your payment")
        if payment.provider_payment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment has no provider payment id",
            )

        provider = get_payment_provider(payment.provider)
        provider_result = provider.confirm_payment(provider_payment_id=payment.provider_payment_id)
        payment = self.payments.update_status(payment, provider_result.status)

        if payment.status == PaymentStatus.PAID:
            order = self.orders.get(payment.order_id)
            if order is not None:
                self.orders.update_status(order, OrderStatus.PAID)
        return payment

    def get_payment_by_order(self, order_id: int, actor: User) -> Payment:
        order = self.orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if actor.role != UserRole.ADMIN and actor.id not in {order.buyer_id, order.seller_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

        payment = self.payments.get_latest_by_order(order_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment
