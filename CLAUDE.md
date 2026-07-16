# Bazart — CLAUDE.md

C2C **muddatli auksion** marketplace (O'zbekiston). Backend: Python 3.12 + FastAPI.

**Muammo:** OLX'da e'lonlar oylab sotilmaydi — deadline yo'q, narx muzlab qoladi.
**Yechim:** har e'londa **majburiy deadline** (3/5/7 kun) + **auksion** + **escrow**.

## Muhim qarorlar (O'ZGARMAYDI)

| Qaror | Sabab |
|---|---|
| Modular monolith, mikroservis EMAS | MVP tezligi, tranzaksiya butunligi |
| PostgreSQL asosiy DB | Pul = ACID |
| Escrow'ni O'ZIMIZ ushlamaymiz | Litsenziya yo'q. PSP hold/capture qiladi, biz orkestratsiya qilamiz |
| **Pul = butun son (tiyin), BIGINT** | Float **TAQIQ**. (Hozirgi kod: `Numeric(12,2)` — migratsiya qilinadi, Faza B) |
| Barcha vaqt UTC | Ko'rsatishda `Asia/Tashkent` |
| Jonli video YO'Q | Pozitsiyaga zid, xarajat + moderatsiya yuki |
| Anti-sniping | <2 daqiqa qolganda bid → end_time +2 daqiqa |
| Proxy bidding (max-bid) | `high_bidder_max` **HECH QACHON** API'da oshkor bo'lmaydi |
| Bid atomik | `SELECT ... FOR UPDATE` majburiy |
| Idempotentlik | Har to'lov operatsiyasi `idempotency_key` bilan |
| Auksion holati faqat state machine orqali | Qo'lda `status = ...` **TAQIQ** |
| Karta PAN hech qachon saqlanmaydi | Faqat PSP token |
| PSP webhook imzosiz qabul qilinmaydi | Soxta "to'landi" = tovar bepul ketadi |
| Buyer premium 8% | BPS = 800 |
| Auto-complete 72 soat | Xaridor sukut saqlasa — order yopiladi |

## Tech stack (REAL)

FastAPI · SQLAlchemy 2.0 (Mapped/mapped_column) · Alembic · PostgreSQL 16 · Pydantic v2 +
pydantic-settings · PyJWT · bcrypt · pytest · ruff · uvicorn · Docker Compose (db + redis + minio) ·
GitHub Actions CI (ruff check + ruff format --check + pytest).

**Ko'tarilgan, lekin kod hali ULANMAGAN:** Redis (compose'da bor — ZSET taymer/kesh/pub-sub uchun),
MinIO (S3-mos; hozir fayllar `uploads/` ga lokal yoziladi).
**Yo'q (hali):** background worker (Celery/ARQ/APScheduler — **tanlov ochiq**), rate limiting.

## Struktura (REAL)

```
app/
  main.py              # create_app(), /api/v1 router, /uploads static mount
  core/                # config.py (Settings), security.py (JWT/bcrypt), dependencies.py (DI)
  db/                  # session.py (engine, get_db), base.py (metadata import)
  models/              # SQLAlchemy: user, item, auction, bid, order, payment, message, category, enums
  schemas/             # Pydantic v2 I/O
  api/v1/router.py     # + endpoints/: auth, users, categories, items, auctions, bids, payments, orders, messages, admin
  repositories/        # DB kirish (select/insert)
  services/            # biznes mantiq: bid_service, auction_service, payment_service, payment_providers, ...
alembic/versions/      # 8 migratsiya
tests/                 # 36 test, hammasi o'tadi
```

Qatlam yo'nalishi: **api → services → repositories → models**. Teskari import TAQIQ.
Biznes mantiq endpoint ichida yozilmaydi — service'ga.

## Kritik biznes qoidalari

1. **Bid atomik bo'lishi shart** — `with_for_update()` bilan auksion qatorini lock qilib.
   Hozir bu YO'Q → race condition mavjud. Bid kodiga tegsang, lock qo'sh.
2. **Sotuvchi o'z lotiga bid qo'yolmaydi** (shill) — `bid_service.py:56-60`.
3. **Min qadam:** `amount >= current_price + minimum_bid_increment`.
4. **Anti-sniping** — `SOFT_CLOSE_WINDOW_SECONDS=120`, `SOFT_CLOSE_EXTENSION_SECONDS=120`.
5. **Mock to'lov faqat local/test** — `settings.allow_mock_payments`. Prod'da mock = bepul tovar.
6. **Prod'da default SECRET_KEY bilan ko'tarilish bloklangan** — `config.py` model_validator.

## Komandalar

```bash
.venv/Scripts/python.exe -m pytest        # 36 test
.venv/Scripts/python.exe -m pytest tests/test_bids.py
ruff check .
ruff format .
alembic upgrade head
alembic revision --autogenerate -m "..."
docker compose up -d db                   # faqat Postgres
docker compose up --build                 # API + Postgres
uvicorn app.main:app --reload
```

## Kod uslubi

- ruff: `line-length = 100`, `target-version = "py312"`, lint: `E,F,I,UP,B`.
- Docstring (JSDoc emas), **o'zbekcha**, `"""..."""`. Nima uchun — muhimroq, nima — emas.
- Type hints majburiy. `Mapped[...]` / `mapped_column(...)` uslubi.
- `datetime.now(UTC)` — naive datetime TAQIQ.
- Pul: hozir `Decimal`; yangi kodda **butun son (tiyin)** ga o'tishga tayyor yoz. `float` TAQIQ.

## Test qoidalari

- Hozir `conftest.py` **SQLite in-memory** ishlatadi → `FOR UPDATE` sinab bo'lmaydi, race testi yo'q.
  **Faza A'da Postgres'ga ko'chiriladi.**
- Har pul/auksion o'zgarishi uchun test majburiy.
- Atomik bid kodini SQLite'da "sinab ko'rdim" deb hisoblama — bu yolg'on ishonch.

## Xavfsizlik

- PAN saqlash TAQIQ. Faqat `token_reference`.
- Webhook imzosiz qabul qilinmaydi (hali webhook YO'Q).
- `high_bidder_max` javob sxemasiga hech qachon qo'shilmaydi.
- IDOR: har resursda egalik tekshiruvi (hozir toza).
- Secret'lar `.env`da, git'ga tushmaydi.

## Ish tartibi

1. O'zgartirishdan oldin tegishli `docs/` faylni o'qi.
2. Model o'zgarsa → Alembic migratsiya majburiy.
3. Biznes qoida o'zgarsa → docs yangilanadi.
4. Kommitdan oldin: `ruff check .` + `pytest`.
5. Xavfsizlik yoki pul mantiqini "keyin tuzatamiz" deb qoldirma — TODO yozib, ROADMAP'ga kirit.

## docs/

| Fayl | Nima haqida |
|---|---|
| `docs/ARCHITECTURE.md` | Tizim arxitekturasi, qatlamlar, oqimlar, nega monolith |
| `docs/DOMAIN.md` | Real jadvallar, ustunlar, enum'lar, maqsadli o'zgarishlar |
| `docs/AUCTION_ENGINE.md` | Atomik bid, proxy bidding, anti-sniping, closer worker, state machine |
| `docs/PAYMENTS.md` | Escrow, PSP adapter, idempotentlik, webhook imzo, audit log, huquq |
| `docs/ROADMAP.md` | Fazalar A→D va keyingilari, bajarilganlar belgilangan |
