# Yo'l xaritasi

Real holatga asoslangan. `[x]` = kodda bor va ishlaydi. `[ ]` = yo'q.

## Bajarilgan poydevor (skelet)

- [x] FastAPI + SQLAlchemy 2 + Alembic + Postgres 16 skeleti
- [x] Qatlamli struktura: api → services → repositories → models
- [x] Auth: register / login / refresh / logout / password reset / email verification (JWT + bcrypt)
- [x] Rollar va DI: `CurrentUser`, `CurrentActiveUser`, `CurrentAdmin`, `require_roles`
- [x] Kategoriyalar (parent-child daraxt)
- [x] E'lonlar (items) + rasm yuklash (`StorageService`, lokal disk)
- [x] Auksion yaratish, min qadam, reserve, g'olib maydonlari
- [x] **Anti-sniping (soft close)** — `bid_service.py:86-97`, testi bor
- [x] **Shill taqiqi** — sotuvchi o'z lotiga bid qo'yolmaydi
- [x] Order yaratish (auksion yopilganda)
- [x] Xabarlar (buyer↔seller, faqat ishtirokchilar)
- [x] Admin moderatsiya + statistika
- [x] **PSP abstraksiyasi** (`BasePaymentProvider` ABC) + provayder registri
- [x] **Karta tokenizatsiya** — PAN saqlanmaydi (`models/payment.py:12-23`)
- [x] **Mock to'lov guard'i** — `allow_mock_payments`, prod/staging'da o'chiq
- [x] **SECRET_KEY guard** — prod'da default secret bilan ilova ko'tarilmaydi
- [x] **IDOR himoyasi** — toza
- [x] **Float ishlatilmagan** — hamma joyda Decimal
- [x] 36 test, hammasi o'tadi (`test_payment_security.py` — 8 ta xavfsizlik testi)
- [x] Docker Compose (api + db), Dockerfile, ruff konfiguratsiyasi

---

## Faza A — Xavfsizlik va poydevor

Maqsad: keyingi ishlar uchun ishonchli zamin. Busiz atomiklikni **sinab bo'lmaydi**.

- [x] `confirm-mock` teshigi yopildi — muhit guard'i (`payment_service.py`), prod'da 404
- [x] `get_payment_provider()` noma'lum nomga jimgina Mock qaytarmaydi — endi xato beradi
- [x] SECRET_KEY guard (`config.py` model_validator)
- [x] **Testlarni Postgres'ga ko'chirish** — real Postgres 16 (host port 5433), `bazart_test`
      avtomatik yaratiladi, TRUNCATE bilan tozalanadi. SQLite butunlay olib tashlandi
- [x] Redis + MinIO qo'shildi (docker-compose + healthcheck) — kod hali ULAMAGAN
- [x] Rate limiting: login (5/daq) va bid (10/daq) endpoint'lariga (`core/rate_limit.py`)
- [x] CI (GitHub Actions): `ruff check` + `ruff format --check` + `pytest` (Postgres+Redis bilan)
- [ ] Strukturaviy logging (JSON) + `request_id`
- [x] `PATCH /auctions/{id}/status` cheklandi — state machine + sotuvchi faqat bekor qila oladi

## Faza B — Pul: Numeric → BIGINT tiyin  ✅ BAJARILDI

- [x] Konvensiya: barcha pul `int` tiyin. `float` TAQIQ. Yagona manba: `app/money/`
- [x] Alembic migratsiya (202607170009): 9 ustun `Numeric(12,2)` → `BIGINT` (qiymat × 100)
      + DB CHECK (narx > 0)
- [x] Modellar va Pydantic sxemalari `int`ga (`TiyinAmount` — JSON'da string)
- [x] Buyer premium (BPS 800) + tiyin arifmetikasi `app/money/` da
- [x] Chegara testlari + migratsiya testi (toza bazada + BIGINT tekshiruvi + `alembic check`)

## Faza C — Auksion dvigateli (mahsulotning yuragi)

- [x] **Atomik bid**: `AuctionRepository.get_for_update()` — validatsiyadan oldin qulf,
      butun oqim bitta tranzaksiyada
- [x] **Race condition testi**: 12 parallel bid, alohida ulanishlar → aynan bitta g'olib.
      Isbotlangan: qulf olib tashlansa test yiqiladi (`test_bid_concurrency.py`)
- [x] **State machine** (`services/auction_state.py`): ruxsat etilgan o'tishlar jadvali,
      qo'lda `status = ...` TAQIQ. close/activate/cancel — hammasi `assert_transition` orqali
- [x] **Closer worker** (`services/auction_closer.py`): `end_time` o'tgan auksionlarni
      avtomatik yopadi, FastAPI lifespan startup'da (APScheduler EMAS — oddiy asyncio loop)
- [x] `scheduled → active` avto-aktivatsiya (bid kelganda, qulf ostida commit'siz)
- [x] **Proxy bidding** (orqaga mos): `auctions.high_bidder_max`, `bids.max_amount`,
      `bids.is_proxy` + leader avtomatik himoyasi (migratsiya 202607170010)
- [x] Test: `high_bidder_max`/`max_amount` API javobida **yo'q** (maxfiylik qalqoni)
- [ ] Worker idempotentligi bo'yicha qo'shimcha test: ikki tik bir auksionni yopsa — bitta order
- [ ] `duration_days` (3/5/7) majburiy qilish — hozir ixtiyoriy `end_time`
- [ ] `extension_count` limiti (anti-sniping cheksiz cho'zilmasin)
- [ ] Kompozit index: `bids(auction_id, amount DESC, created_at ASC)`

## Faza D — Escrow, idempotentlik, audit

- [ ] **Yurist bilan tekshirish**: hold/capture modeli litsenziya talab qiladimi (BLOKER)
- [ ] `PaymentStatus`: `HOLD`, `RELEASED`, `CANCELLED_HOLD` qo'shish
- [ ] `payments.idempotency_key` (unique) + `get_by_idempotency_key()`
- [ ] `BasePaymentProvider`ni escrow shartnomasiga kengaytirish: `create_hold` / `capture` /
      `release` / `verify_webhook`
- [ ] Real PSP adapteri (Payme yoki Click — shartnomaga qarab)
- [ ] **Webhook endpoint + imzo tekshiruvi** (xom bayt, `hmac.compare_digest`, replay himoyasi)
- [ ] `audit_log` jadvali (INSERT only) + pul operatsiyalariga ulash
- [ ] Buyer premium 8% (BPS 800), butun bo'linma bilan hisob
- [ ] Auto-complete 72 soat (worker) + `orders.auto_complete_at`
- [ ] Mock provayderni prod build'dan butunlay olib tashlash

---

## Fazadan keyin

| Bosqich | Nima |
|---|---|
| Real-time | FastAPI WebSocket `/ws/auctions/{id}` — narx, qolgan vaqt, cho'zilish. Fan-out Redis pub/sub. Jonli video YO'Q |
| Handover | Topshirish oqimi: kod/QR tasdiq, uchrashuv joyi, `handover_confirmed_at` |
| Xabarnomalar | Outbid, yutdingiz, deadline yaqin, to'lov kutilmoqda. SMS/push |
| Anti-fraud | Shill halqalari (bir guruh bir-birini ko'tarishi), yangi akkaunt limitlari, qurilma barmoq izi, sotuvchi reytingi |
| Nizolar | Dispute oqimi, admin arbitraj, `release` qarori |
| Mobil | Mobil klient (API allaqachon shunga mo'ljallangan) |
| Beta | Cheklangan kategoriya + Toshkent, real pul, kichik hajm |

## Qat'iy tartib qoidasi

Fazalar **ketma-ket**. Sabab:
- Faza C (atomik bid) Faza A'siz **sinab bo'lmaydi** — SQLite `FOR UPDATE`ni indamay yutadi,
  test yashil bo'ladi, prod'da ma'lumot buziladi.
- Faza D (escrow) Faza B'siz — Numeric/int aralashmasi pul hisobida xatoga olib keladi.
- Real-time Faza C'siz — noto'g'ri narxni tez tarqatishdan boshqa foyda yo'q.

Yangi feature Faza A–D tugamasdan qo'shilmaydi.
