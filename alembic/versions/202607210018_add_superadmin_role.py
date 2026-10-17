"""user_role enum: 'SUPERADMIN' qiymatini qo'shish

Superadmin — adminning ustki to'plami. Rol berish va adminlarni boshqarish
kabi sezgir amallar faqat shu rolga ochiladi.

Eslatma: SQLAlchemy enum ustunini NOM (katta harf) sifatida saqlaydi
(user_role: 'USER'/'SELLER'/'ADMIN'). Shuning uchun yangi qiymat ham katta
harfda — 'SUPERADMIN'.

Revision ID: 202607210018
Revises: 202607210017
"""

from alembic import op

revision: str = "202607210018"
down_revision: str | None = "202607210017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL 12+ da ADD VALUE tranzaksiya ichida ishlaydi (qiymat shu
    # tranzaksiyada ishlatilmaydi — faqat qo'shiladi).
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'SUPERADMIN'")


def downgrade() -> None:
    # Enum'dan qiymat olib tashlash — turni qayta qurish orqali. Avval mavjud
    # superadminlarni 'ADMIN' ga tushiramiz, so'ng turni SUPERADMIN'siz tiklaymiz.
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'SUPERADMIN'")
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('USER', 'SELLER', 'ADMIN')")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::text::user_role")
    op.execute("DROP TYPE user_role_old")
