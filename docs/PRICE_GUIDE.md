# Telefon narx ko'rsatkichi

Ishlatilgan iPhone'ning taxminiy bozor bahosi: model, xotira, tashqi holat darajasi,
batareya va nosozliklar bo'yicha. G'oya — Fongabi.com (Koreya) dagi "오늘의 시세"
(bugungi narxlar): narx shaffofligi sotuvchiga to'g'ri boshlang'ich narx, xaridorga
taklif chegarasi beradi.

## Manba

`scripts/price_guide_apple.json` — `Apple_Used_Price_List_EN.xlsx` (PS Trading Company,
Koreya) dan bir martalik konvertatsiya. **Koreya diler buy-back narxlari, WON'da**
(jadvaldagi birlik 10 000 won — JSON'da butun won'ga o'girilgan). 42 model, 122 xotira
qatori: iPhone 6 dan 17 Pro Max gacha.

Jadval o'qish qoidalari (konvertatsiyada qo'llangan):
- `X` (B- ustunida) → shu darajada sotib olinmaydi → `null`.
- `차감X` / "No deduction" → ajratma 0.
- `-3.5(-2)` (LCD) → `lcd = 35 000`, `lcd_uninspectable = 20 000`.
- "Genuine-parts message 1 item: -N" — seriya guruhi bo'yicha keyingi matngacha amal qiladi.
- Past ishonchli kataklar (manba izohi): SE 3 64G B+, 16 128G B+/batareya, 7 va XS Max
  kamera ajratmasi (musbat yozilgan — modul olingan).

Yangilash: yangi jadvalni JSON'ga o'tkazib `python scripts/seed_price_guide.py` —
idempotent (model `slug`, narx `(model, xotira)` bo'yicha yangilanadi).

## Jadvallar

| Jadval | Nima |
|---|---|
| `device_models` | brand, name, slug, series, ajratmalar `*_krw`, `scrap_krw` |
| `device_prices` | (model, storage) UNIQUE; `grade_a/a_minus/b_plus/b_minus_krw`, `battery_low_a/b_plus_krw`, `base_krw` |
| `price_guide_settings` | bitta qator (id=1): `rate_tiyin_per_krw`, `market_adjust_bps` |
| `items.device_*` | `device_model_id`, `device_storage`, `device_grade` (ENUM), `battery_health`, `device_defects` (JSON) |

`*_krw` — pul emas, **manba ma'lumot** (won). Foydalanuvchiga chiqadigan har narx
tiyinga `app/money.convert_foreign_to_tiyin` orqali o'giriladi.

## O'girish

`tiyin = krw × rate_tiyin_per_krw × (10000 + market_adjust_bps) // 10000`, keyin
**1 000 so'mga pastga** yaxlitlanadi (taxminiy bahoni oshirib ko'rsatmaslik uchun).
Default: 1 won = 8.55 so'm (855 tiyin, Wise mid-market, 2026-avgust), tuzatma 0.
Admin: `/admin/price-guide` (`PUT /admin/price-guide/settings`) — saqlangach barcha
narxlar darhol qayta hisoblanadi (manba won o'zgarmaydi).

Tuzatma nima uchun: manba — dilerning **sotib olish** narxi Koreyada. O'zbekistondagi
C2C narx odatda yuqoriroq; admin bozorga qarab `+N%` beradi.

## Baho qoidalari (`PriceGuideService.estimate`)

1. Daraja narxi (A / A- / B+ / B-). Daraja berilmasa yoki shu darajada `null` → `base`.
2. Batareya darajaning me'yoridan past (A/A- < 90, B+ < 85, B- < 81): jadvaldagi
   "batareya past" narxi, bo'lmasa bir daraja past narx (u ham bo'lmasa `base`).
3. Har nosozlik ajratmasi ayiriladi (takroriylar bir marta).
4. Natija `scrap` narxidan pastga tushmaydi (`floored_to_scrap`).

## API

| Endpoint | |
|---|---|
| `GET /price-guide` | modellar + kurs ma'lumoti (ochiq) |
| `GET /price-guide/models/{slug}` | xotira × daraja narxlari, ajratmalar (so'mda) |
| `POST /price-guide/estimate` | taxminiy baho (ochiq, rate limit) |
| `GET/PUT /admin/price-guide/settings` | kurs va tuzatma (admin) |

## UI

- `/narxlar` — modellar ro'yxati (qidiruv), jadval, daraja mezonlari, ajratmalar.
- Sotish formasi (faqat `telefonlar` kategoriyasi) — model/xotira/daraja/batareya/nosozlik,
  jonli baho, "Narxni qo'llash" (tavsiya boshlang'ich narx = bahoning 80%, 10 000 so'mga pastga).
- Lot kartochkasi va sahifasi — daraja/xotira/batareya belgilari, "Taxminiy bozor bahosi"
  va joriy narx bilan solishtirish.

Har joyda manba va kurs ko'rsatiladi; bu **kafolatlangan narx emas**.
