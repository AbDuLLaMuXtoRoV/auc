"""To'lov (escrow) holati state machine.

Escrow oqimi: PENDING -> HELD -> RELEASED (normal), yoki HELD ->
CANCELLED_HOLD (nizo). Pul holati faqat shu o'tishlar orqali o'zgaradi —
qo'lda `payment.status = ...` yozish escrow invariantlarini buzadi
(masalan hold bo'lmasdan RELEASED, yoki ikki marta capture).

Eslatma: eski mock intent oqimi (PENDING -> PAID) bu state machine'dan
o'tmaydi — u alohida, faqat local/test uchun.
"""

from app.models.enums import PaymentStatus

ALLOWED_TRANSITIONS: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.PENDING: frozenset({PaymentStatus.HELD, PaymentStatus.FAILED}),
    PaymentStatus.HELD: frozenset({PaymentStatus.RELEASED, PaymentStatus.CANCELLED_HOLD}),
    # Yakuniy holatlar:
    PaymentStatus.RELEASED: frozenset(),
    PaymentStatus.CANCELLED_HOLD: frozenset(),
    PaymentStatus.FAILED: frozenset(),
    PaymentStatus.REFUNDED: frozenset(),
    PaymentStatus.PAID: frozenset(),  # eski mock oqimi (terminal)
}


class InvalidPaymentTransition(Exception):
    """Taqiqlangan to'lov holati o'tishi."""

    def __init__(self, current: PaymentStatus, target: PaymentStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"To'lov holati {current.value} -> {target.value} taqiqlangan")


def assert_payment_transition(current: PaymentStatus, target: PaymentStatus) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidPaymentTransition(current, target)
