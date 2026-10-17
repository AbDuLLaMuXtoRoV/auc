from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dispute import Dispute
from app.models.enums import DisputeReason, DisputeStatus, PaymentStatus, is_admin
from app.models.user import User
from app.repositories.dispute_repository import OPEN_STATUSES, DisputeRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService


class DisputeService:
    """Nizo oqimi: xaridor HELD hold ustidan nizo ochadi, admin hal qiladi.

    Pul harakati PaymentService orqali (capture/release) — bu yerda qo'lda
    payment status o'zgartirilmaydi. Admin qarori pulni sotuvchiga (capture)
    yoki xaridorga (release) yo'naltiradi.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.payments = PaymentRepository(db)
        self.disputes = DisputeRepository(db)

    def open_dispute(
        self,
        order_id: int,
        opener: User,
        reason: DisputeReason,
        description: str | None,
    ) -> Dispute:
        """Xaridor nizo ochadi. Faqat o'z order'iga, faqat faol HELD hold
        bo'lganda va shu order uchun boshqa ochiq nizo bo'lmasa."""
        order = self.orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.buyer_id != opener.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

        payment = self.payments.get_latest_by_order(order_id)
        if payment is None or payment.status != PaymentStatus.HELD:
            # Faol hold yo'q -> nizoning ma'nosi yo'q (pul bloklanmagan).
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order uchun faol hold yo'q",
            )

        if self.disputes.get_open_by_order(order_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu order uchun ochiq nizo allaqachon mavjud",
            )

        dispute = self.disputes.create(
            order_id=order_id,
            payment_id=payment.id,
            opened_by=opener.id,
            reason=reason,
            description=description,
        )
        self.db.commit()
        self.db.refresh(dispute)
        return dispute

    def resolve(
        self,
        dispute_id: int,
        admin: User,
        decision: str,
        resolution: str,
    ) -> Dispute:
        """Admin nizoni hal qiladi. decision "buyer" -> release, "seller" ->
        capture.

        Atomiklik: dispute maydonlari AVVAL yoziladi (commit QILINMAYDI),
        so'ng PaymentService.capture/release chaqiriladi — u bitta commit
        bilan payment + order + dispute o'zgarishlarini birga saqlaydi.
        Agar payment operatsiyasi xato bersa (masalan HELD emas), commit
        bo'lmaydi va session yopilganda dispute o'zgarishlari ham qaytadi —
        yarim holat qolmaydi.
        """
        if not is_admin(admin.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
            )
        # decision qat'iy {"buyer","seller"} — aks holda jimgina capture bo'lib
        # pul noto'g'ri tomonga ketardi (review topilmasi).
        if decision not in {"buyer", "seller"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="decision 'buyer' yoki 'seller' bo'lishi kerak",
            )

        # Qulflab o'qiymiz — ikki parallel resolve biri capture biri release
        # qilib qo'ymasin (TOCTOU).
        dispute = self.disputes.get_for_update(dispute_id)
        if dispute is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
        if dispute.status not in OPEN_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Dispute is already resolved"
            )

        dispute.resolved_by = admin.id
        dispute.resolved_at = datetime.now(UTC)
        dispute.resolution = resolution

        payment_service = PaymentService(self.db)
        if decision == "buyer":
            dispute.status = DisputeStatus.RESOLVED_BUYER
            self.db.flush()  # dispute o'zgarishlarini sessiyaga qo'yamiz
            payment_service.release_hold(
                dispute.payment_id, f"dispute-release:{dispute_id}", actor=admin
            )
        else:
            dispute.status = DisputeStatus.RESOLVED_SELLER
            self.db.flush()
            payment_service.capture_payment(
                dispute.payment_id, f"dispute-capture:{dispute_id}", actor=admin
            )

        # PaymentService odatda o'zi commit qiladi; idempotent erta-qaytish
        # yo'li commit qilmasligi mumkin — dispute o'zgarishini kafolatlaymiz.
        self.db.commit()
        self.db.refresh(dispute)
        return dispute

    def get_for_user(self, dispute_id: int, user: User) -> Dispute:
        """Nizoni ochuvchi yoki admin ko'ra oladi."""
        dispute = self.disputes.get(dispute_id)
        if dispute is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
        if not is_admin(user.role) and dispute.opened_by != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your dispute")
        return dispute

    def list_mine(self, user: User) -> list[Dispute]:
        return self.disputes.list_by_user(user.id)

    def list_open_for_admin(self, admin: User) -> list[Dispute]:
        if not is_admin(admin.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
            )
        return self.disputes.list_by_status(OPEN_STATUSES)
