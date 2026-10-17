"""payment_status enum: escrow qiymatlari katta harfga (nom bilan saqlanadi)

Muammo: SQLAlchemy enum ustunlari qiymatni NOM (katta harf) sifatida saqlaydi
(auction_status='ENDED', order_status='PENDING_PAYMENT' kabi). Ammo escrow
migratsiyasi (012) payment_status'ga 'held'/'released'/'cancelled_hold' ni
KICHIK harfda qo'shgan. Natijada model PaymentStatus.HELD -> "HELD" yozadi,
lekin bazada 'held' bo'lgani uchun `invalid input value for enum` xatosi chiqadi
(escrow hold 500 beradi). Bu yerda uch qiymatni katta harfga o'tkazamiz.

Revision ID: 202607210017
Revises: 202607170016
"""

from alembic import op

revision: str = "202607210017"
down_revision: str | None = "202607170016"
branch_labels = None
depends_on = None

_RENAMES = [
    ("held", "HELD"),
    ("released", "RELEASED"),
    ("cancelled_hold", "CANCELLED_HOLD"),
]


def upgrade() -> None:
    for old, new in _RENAMES:
        op.execute(f"ALTER TYPE payment_status RENAME VALUE '{old}' TO '{new}'")


def downgrade() -> None:
    for old, new in _RENAMES:
        op.execute(f"ALTER TYPE payment_status RENAME VALUE '{new}' TO '{old}'")
