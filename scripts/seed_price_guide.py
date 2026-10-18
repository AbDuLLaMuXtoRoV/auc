"""Telefon narx ko'rsatkichini (`price_guide_apple.json`) bazaga yuklaydi.

Manba: Apple_Used_Price_List_EN.xlsx (Koreya, PS Trading Company buy-back
narxlari) — bir martalik konvertatsiya bilan JSON'ga o'tkazilgan, qiymatlar
butun WON'da.

Idempotent: model `slug` bo'yicha, narx (model, xotira) bo'yicha yangilanadi —
yangi jadval kelganda JSON'ni almashtirib qayta ishga tushirish kifoya.
Kurs sozlamasi faqat YO'Q bo'lsa yaratiladi (admin o'zgartirgan kurs saqlanadi).

Foydalanish (loyiha ildizidan):
    python scripts/seed_price_guide.py
    python scripts/seed_price_guide.py path/to/other.json
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.db.base  # noqa: E402, F401  (barcha modellarni registratsiya qiladi)
from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.price_guide import DeviceModel, DevicePrice  # noqa: E402
from app.repositories.price_guide_repository import PriceGuideRepository  # noqa: E402

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_guide_apple.json")

_PRICE_FIELDS = {
    "a": "grade_a_krw",
    "a_minus": "grade_a_minus_krw",
    "b_plus": "grade_b_plus_krw",
    "b_minus": "grade_b_minus_krw",
    "battery_low_a": "battery_low_a_krw",
    "battery_low_b_plus": "battery_low_b_plus_krw",
    "base": "base_krw",
}


def main(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("currency") != "KRW":
        print("XATO: faqat KRW (won) manbasi qo'llab-quvvatlanadi.")
        return 1

    db = SessionLocal()
    try:
        repo = PriceGuideRepository(db)
        created_models = updated_models = created_prices = 0
        for entry in data["models"]:
            model = repo.get_model_by_slug(entry["slug"])
            if model is None:
                model = DeviceModel(slug=entry["slug"])
                db.add(model)
                created_models += 1
            else:
                updated_models += 1
            model.brand = entry["brand"]
            model.name = entry["name"]
            model.series = entry["series"]
            model.sort_order = entry["sort_order"]
            for key, amount in entry["deductions_krw"].items():
                setattr(model, f"{key}_krw", amount)
            model.scrap_krw = entry["scrap_krw"]
            db.flush()

            existing = {p.storage: p for p in model.prices}
            for index, row in enumerate(entry["prices"]):
                price = existing.get(row["storage"])
                if price is None:
                    price = DevicePrice(model_id=model.id, storage=row["storage"])
                    model.prices.append(price)
                    created_prices += 1
                price.sort_order = index
                for key, column in _PRICE_FIELDS.items():
                    setattr(price, column, row[key])

        if repo.get_settings() is None:
            repo.save_settings(
                rate_tiyin_per_krw=settings.price_guide_default_rate_tiyin_per_krw,
                market_adjust_bps=settings.price_guide_default_market_adjust_bps,
                updated_by_id=None,
            )
            print("Kurs sozlamasi yaratildi (default).")
        db.commit()
        print(
            f"OK: modellar — {created_models} yangi, {updated_models} yangilandi; "
            f"{created_prices} yangi narx qatori."
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH))
