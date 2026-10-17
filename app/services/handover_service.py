import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import (
    HandoverMethod,
    HandoverStatus,
    OrderStatus,
    PaymentStatus,
    is_admin,
)
from app.models.handover import Handover
from app.models.user import User
from app.repositories.handover_repository import HandoverRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService


def _generate_code() -> str:
    """6 xonali tasdiqlash kodi.

    `secrets` ishlatiladi (`random` EMAS) — kod egalik dalili, taxmin qilib
    bo'lmasligi kerak.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


class HandoverService:
    """Tovar topshirish oqimi: yaratish -> kod -> tasdiqlash -> capture.

    Oqim: order PICKUP_PENDING (pul hold qilingan) bo'lganda sotuvchi handover
    yaratadi va kod oladi. Uchrashuvda kodni xaridorga aytadi. Xaridor kodni
    kiritib tasdiqlaydi -> HELD to'lov capture bo'ladi (pul sotuvchiga),
    order COMPLETED bo'ladi.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.handovers = HandoverRepository(db)
        self.orders = OrderRepository(db)
        self.payments = PaymentRepository(db)

    def create_handover(
        self,
        order_id: int,
        seller: User,
        method: HandoverMethod = HandoverMethod.LOCAL_MEETUP,
        meet_address: str | None = None,
    ) -> Handover:
        """Sotuvchi topshirishni boshlaydi va tasdiqlash kodini oladi.

        Idempotent: handover allaqachon mavjud bo'lsa, yangisini yaratmasdan
        uni qaytaradi (kod o'zgarmaydi).
        """
        order = self.orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.seller_id != seller.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
        if order.status != OrderStatus.PICKUP_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order to'lov hold holatida emas",
            )

        existing = self.handovers.get_by_order_id(order_id)
        if existing is not None:
            return existing  # idempotent — kod qayta generatsiya qilinmaydi

        handover = Handover(
            order_id=order_id,
            method=method,
            code=_generate_code(),
            status=HandoverStatus.PENDING,
            meet_address=meet_address,
        )
        self.handovers.create(handover)
        self.db.commit()
        self.db.refresh(handover)
        return handover

    def confirm_handover(self, order_id: int, buyer: User, code: str) -> Handover:
        """Xaridor kodni kiritadi; to'g'ri bo'lsa capture ishga tushadi.

        Tartib: avval handover holatini o'zgartirib flush qilamiz, keyin
        `capture_payment` chaqiramiz — u yagona commit'ni bajaradi. Shunday
        qilib handover COMPLETED va payment RELEASED bitta izchil tranzaksiyada
        yoziladi (ikkita alohida commit bo'lmaydi).
        """
        handover = self.handovers.get_by_order_id(order_id)
        if handover is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover not found")

        order = self.orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.buyer_id != buyer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
        if handover.status != HandoverStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Handover PENDING holatida emas",
            )
        # Doimiy vaqtli taqqoslash — kod taxminlashga qarshi.
        if not secrets.compare_digest(handover.code, code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Noto'g'ri kod")

        payment = self.payments.get_latest_by_order(order_id)
        if payment is None or payment.status != PaymentStatus.HELD:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Capture uchun HELD to'lov topilmadi",
            )

        handover.status = HandoverStatus.COMPLETED
        handover.confirmed_at = datetime.now(UTC)
        self.handovers.save(handover)  # flush — commit'ni capture_payment bajaradi

        # capture_payment: HELD -> RELEASED, order COMPLETED, audit, commit.
        PaymentService(self.db).capture_payment(
            payment.id, f"handover-capture:{order_id}", actor=buyer
        )

        self.db.refresh(handover)
        return handover

    def get_for_participant(self, order_id: int, user: User) -> Handover:
        """Order ishtirokchisi (buyer/seller/admin) handoverni ko'radi.

        KOD faqat sotuvchiga (yoki adminga) ko'rsatiladi. Bu metod ORM
        obyektini qaytaradi; kodni yashirish javob qatlamida (endpoint)
        `is_code_visible` orqali hal qilinadi.
        """
        handover = self.handovers.get_by_order_id(order_id)
        if handover is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover not found")

        order = self.orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if not is_admin(user.role) and user.id not in {order.buyer_id, order.seller_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")
        return handover

    @staticmethod
    def is_code_visible(handover: Handover, user: User) -> bool:
        """Kod faqat sotuvchi va adminga ko'rinadi."""
        return is_admin(user.role) or user.id == handover.order.seller_id
