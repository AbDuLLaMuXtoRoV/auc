"""Pul arifmetikasi. Pul HAR DOIM tiyinda (butun son).

Nega tiyin (butun son), Decimal/float emas:
- float bilan pul TAQIQ — 0.1 + 0.2 != 0.3, yaxlitlash xatolari yig'iladi.
- Decimal xavfsiz, lekin har amalda kontekst/aniqlik masalasi tug'iladi
  va JSON/DB chegaralarida jimgina float'ga aylanib ketishi mumkin.
- Butun son tiyin: bitta haqiqat, yaxlitlash faqat bitta joyda
  (calc_buyer_premium ichida), taqqoslash va yig'indi aniq.

1 so'm = 100 tiyin.
"""

from app.money.money import (
    BUYER_PREMIUM_BPS,
    Tiyin,
    calc_buyer_premium,
    calc_seller_payout,
    calc_total,
    format_soum,
    soum_to_tiyin,
    tiyin_to_soum,
)

__all__ = [
    "BUYER_PREMIUM_BPS",
    "Tiyin",
    "calc_buyer_premium",
    "calc_seller_payout",
    "calc_total",
    "format_soum",
    "soum_to_tiyin",
    "tiyin_to_soum",
]
