"""Superadmin yaratish yoki mavjud foydalanuvchini superadminga ko'tarish.

Superadmin ro'yxatdan o'tish oqami orqali OLINMAYDI (rol berish faqat
superadminga ochiq) — shuning uchun birinchi superadmin shu skript bilan,
server yonida qo'lda yaratiladi.

Foydalanish:
    python scripts/create_superadmin.py --email admin@bazart.uz --password 'Parol123'
    python scripts/create_superadmin.py --email admin@bazart.uz            # mavjudni ko'tarish

Yoki muhit o'zgaruvchilari bilan:
    SUPERADMIN_EMAIL=... SUPERADMIN_PASSWORD=... python scripts/create_superadmin.py
"""

from __future__ import annotations

import argparse
import os
import sys

# Skript loyiha ildizidan ishga tushiriladi — `app` paketi import qilinsin.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.db.base  # noqa: E402, F401  (barcha modellarni registratsiya qiladi)
from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402
from app.schemas.user import UserCreate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Superadmin yaratish/ko'tarish")
    parser.add_argument("--email", default=os.getenv("SUPERADMIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("SUPERADMIN_PASSWORD"))
    parser.add_argument("--full-name", default=os.getenv("SUPERADMIN_NAME", "Superadmin"))
    args = parser.parse_args()

    if not args.email:
        parser.error("--email (yoki SUPERADMIN_EMAIL) majburiy")

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        user = repo.get_by_email(args.email)

        if user is None:
            if not args.password:
                parser.error(
                    "Yangi foydalanuvchi uchun --password (yoki SUPERADMIN_PASSWORD) majburiy"
                )
            user = repo.create(
                UserCreate(email=args.email, password=args.password, full_name=args.full_name)
            )
            repo.mark_verified(user)
            action = "yaratildi"
        else:
            if args.password:
                repo.update_password(user, args.password)
            action = "ko'tarildi"

        repo.set_role(user, UserRole.SUPERADMIN)
        print(f"OK: {user.email} (id={user.id}) superadmin sifatida {action}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
