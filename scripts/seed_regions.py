"""O'zbekiston hududlarini (viloyatlar + Qoraqalpog'iston + Toshkent shahri)
bazaga yuklaydi.

14 hudud: 12 viloyat + Qoraqalpog'iston Respublikasi + Toshkent shahri,
va ularning tumanlari/shaharlari (`districts_data.py`).

Idempotent: `code` bo'yicha mavjud hudud va (hudud, name_uz) bo'yicha mavjud
tuman qayta yaratilmaydi, faqat yo'qlari qo'shiladi. Qayta ishga tushirish xavfsiz.

Foydalanish (loyiha ildizidan):
    python scripts/seed_regions.py
"""

from __future__ import annotations

import os
import sys

# Skript loyiha ildizidan ishga tushiriladi — `app` paketi import qilinsin.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from districts_data import DISTRICTS  # noqa: E402

import app.db.base  # noqa: E402, F401  (barcha modellarni registratsiya qiladi)
from app.db.session import SessionLocal  # noqa: E402
from app.models.region import District, Region  # noqa: E402
from app.repositories.region_repository import RegionRepository  # noqa: E402

# (code, name_uz, name_ru). code — barqaror mashina identifikatori.
REGIONS: list[tuple[str, str, str]] = [
    ("TAS_CITY", "Toshkent shahri", "город Ташкент"),
    ("TAS", "Toshkent viloyati", "Ташкентская область"),
    ("AND", "Andijon viloyati", "Андижанская область"),
    ("BUX", "Buxoro viloyati", "Бухарская область"),
    ("FAR", "Farg'ona viloyati", "Ферганская область"),
    ("JIZ", "Jizzax viloyati", "Джизакская область"),
    ("XOR", "Xorazm viloyati", "Хорезмская область"),
    ("NAM", "Namangan viloyati", "Наманганская область"),
    ("NAV", "Navoiy viloyati", "Навоийская область"),
    ("QAS", "Qashqadaryo viloyati", "Кашкадарьинская область"),
    ("SAM", "Samarqand viloyati", "Самаркандская область"),
    ("SIR", "Sirdaryo viloyati", "Сырдарьинская область"),
    ("SUR", "Surxondaryo viloyati", "Сурхандарьинская область"),
    ("QQR", "Qoraqalpog'iston Respublikasi", "Республика Каракалпакстан"),
]


def main() -> int:
    db = SessionLocal()
    try:
        repo = RegionRepository(db)
        created = 0
        for code, name_uz, name_ru in REGIONS:
            if repo.get_by_code(code) is not None:
                continue
            db.add(Region(code=code, name_uz=name_uz, name_ru=name_ru))
            created += 1
        db.commit()
        print(f"OK: {created} yangi hudud qo'shildi ({len(REGIONS)} tadan).")

        districts_created = 0
        districts_total = 0
        for code, districts in DISTRICTS.items():
            region = repo.get_by_code(code)
            if region is None:
                continue
            existing = {d.name_uz for d in repo.list_districts(region.id)}
            for name_uz, name_ru in districts:
                districts_total += 1
                if name_uz in existing:
                    continue
                db.add(District(region_id=region.id, name_uz=name_uz, name_ru=name_ru))
                districts_created += 1
        db.commit()
        print(f"OK: {districts_created} yangi tuman qo'shildi ({districts_total} tadan).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
