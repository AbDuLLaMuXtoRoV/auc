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

- [x] `confirm-mock` teshigi yopildi — muhit guard'i (`payment_service.py:66-67`), prod'da 404
- [x] `get_payment_provider()` noma'lum nomga jimgina Mock qaytarmaydi — endi xato beradi
- [x] SECRET_KEY guard (`config.py` model_validator)
- [ ] **Testlarni Postgres'ga ko'chirish** — hozir SQLite in-memory → `FOR UPDATE` sinalmaydi.
      Testcontainers yoki CI'dagi postgres servisi. **Bu Faza C uchun blokerdir.**
- [ ] Redis qo'shish (docker-compose + settings) — rate limiting, cache, keyin real-time uchun
- [ ] Rate limiting: login, register, bid, payment endpoint'lariga
- [ ] CI (GitHub Actions): `ruff check .` + `pytest` (Postgres bilan) har PR'da
- [ ] Strukturaviy logging (JSON) + `request_id`
- [ ] `PATCH /auctions/{id}/status` ni cheklash — hozir sotuvchi istalgan holatni qo'ya oladi

## Faza B — Pul: Numeric → BIGINT tiyin

- [ ] Konvensiya: barcha pul `int` tiyin. `float` TAQIQ (linter qoidasi bilan qo'riqlash)
- [ ] Alembic migratsiya: `items.starting_price/reserve_price`, `auctions.starting_price/
      current_price/minimum_bid_increment/reserve_price`, `bids.amount`, `orders.final_price`,
      `payments.amount` → `BIGINT` (qiymat × 100)
- [ ] Modellar va Pydantic sxemalarini `int`ga o'tkazish
- [ ] Formatlash yordamchisi: tiyin → "1 250 000 so'm" (faqat ko'rsatish qatlamida)
- [ ] Chegara testlari: 0, 1 tiyin, juda katta summa, yaxlitlash

## Faza C — Auksion dvigateli (mahsulotning yuragi)

Faza A'dagi Postgres testlari **tayyor bo'lgandan keyin** boshlanadi.

- [ ] **Atomik bid**: `select(Auction).where(...).with_for_update()` — validatsiyadan oldin
- [ ] **Race condition testi**: N parallel bid → aynan bitta g'olib (Postgres'da)
- [ ] **State machine**: `transition()` funksiyasi, ruxsat etilgan o'tishlar jadvali,
      to'g'ridan-to'g'ri `status = ...` yozishni yo'q qilish
- [ ] **Closer worker**: `end_time` o'tgan auksionlarni avtomatik yopish (`skip_locked=True`).
      **Runner tanlovi ochiq:** ARQ / APScheduler / Celery — shu fazada hal qilinadi
- [ ] Worker idempotentligi: ikki marta ishlasa — bitta order
- [ ] `scheduled → active` avto-aktivatsiya worker orqali (hozir faqat bid kelganda)
- [ ] **Proxy bidding**: `auctions.high_bidder_max`, `bids.max_amount` maydonlari + algoritm
- [ ] Test: `high_bidder_max` API javobida **yo'q** (maxfiylik regressiya qalqoni)
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
