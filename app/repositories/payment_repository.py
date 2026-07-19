from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PaymentStatus
from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        order_id: int,
        buyer_id: int,
        amount,
        currency: str,
        provider: str,
        provider_payment_id: str | None,
    ) -> Payment:
        payment = Payment(
            order_id=order_id,
            buyer_id=buyer_id,
            amount=amount,
            currency=currency,
            provider=provider,
            provider_payment_id=provider_payment_id,
            status=PaymentStatus.PENDING,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get(self, payment_id: int) -> Payment | None:
        return self.db.get(Payment, payment_id)

    def get_for_update(self, payment_id: int) -> Payment | None:
        """To'lov qatorini QULFLAB o'qiydi (SELECT ... FOR UPDATE).

        capture/release uchun: parallel ikki oqim (handover capture +
        auto-complete, yoki capture vs release) bir vaqtda HELD ni o'qib
        ikki marta settlement yubormasligi uchun. Qulf tranzaksiya
        tugaguncha ushlanadi — chaqiruvchi commit qilmasligi kerak.
        """
        statement = select(Payment).where(Payment.id == payment_id).with_for_update()
        return self.db.scalars(statement).one_or_none()

    def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        statement = select(Payment).where(Payment.idempotency_key == idempotency_key)
        return self.db.scalar(statement)

    def get_latest_by_order(self, order_id: int) -> Payment | None:
        statement = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def update_status(self, payment: Payment, status: PaymentStatus) -> Payment:
        payment.status = status
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment
