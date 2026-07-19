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
- [x] Worker idempotentligi testi: 2 parallel yopish → aynan bitta order (`test_closer_idempotency`)
- [x] `duration_days` (3/5/7) orqali muddat — orqaga mos (end_time ham ishlaydi)
- [x] `extension_count` limiti — anti-sniping ko'pi bilan `max_soft_close_extensions` marta
- [x] Kompozit index: `ix_bids_auction_amount_created` (auction_id, amount, created_at)

**Faza C ✅ BAJARILDI.** Qolgan mayda ishlar (`duration_days` ni to'liq majburiy
qilib `end_time` yo'lini olib tashlash) frontend tayyor bo'lganda.

## Faza D — Escrow, idempotentlik, audit  (asosan BAJARILDI)

- [ ] **Yurist bilan tekshirish**: hold/capture modeli litsenziya talab qiladimi (BLOKER, biznes)
- [x] `PaymentStatus`: `HELD` / `RELEASED` / `CANCELLED_HOLD` (migratsiya 202607170012)
- [x] `payments.idempotency_key` (partial unique) + `get_by_idempotency_key()`
- [x] `BasePaymentProvider` escrow shartnomasi: `create_hold` / `capture` / `release` + Mock
- [x] Escrow state machine (`payment_state.py`) + hold/capture/release oqimi (`payment_service.py`)
- [x] **Webhook imzo tekshiruvi** (`core/webhook.py`: HMAC, xom bayt, compare_digest, replay);
      `POST /payments/webhooks/psp` — imzosiz 401
- [x] `audit_log` jadvali (INSERT only) + pul operatsiyalariga ulangan (HELD/RELEASED/...)
- [x] Buyer premium 8% (BPS 800), `money.calc_buyer_premium` (butun bo'linma)
- [x] Auto-complete 72 soat worker (`auto_complete.py`) + `orders.auto_complete_at`
- [ ] Webhook hodisasini payment holatiga ulash (event->status, `provider_event_id` idempotent)
- [ ] Real PSP adapteri (Payme/Click) — huquqiy tekshiruvdan keyin
- [ ] Mock provayderni prod build'dan butunlay olib tashlash (real PSP kelganda)

**Faza D yadrosi ✅.** Qolgani tashqi bog'liq: yurist xulosasi + real PSP shartnomasi.

---

## Fazadan keyin

| Bosqich | Holat |
|---|---|
| **Real-time** | ✅ WebSocket `/ws/auctions/{id}` + ConnectionManager (relay). Redis pub/sub (ko'p instansiya) va bid'da avto-broadcast — TODO |
| **Handover** | ✅ Kod bilan tasdiq oqimi (`handover_service`), kod yashirin, tasdiq -> capture |
| **Xabarnomalar** | ✅ In-app (`notification_service`), OUTBID/WON/SOLD eventlarga ulangan. SMS/push — TODO |
| **Anti-fraud** | ✅ Signal tahlili (`fraud_service`): bir device/IP ko'p akkaunt, shill overlap, velocity. `bids.ip/device_id`. Admin endpoint |
| **Nizolar** | ✅ Dispute oqimi (`dispute_service`): xaridor ochadi, admin capture/release. Auto-complete ochiq nizoda to'xtaydi |
| **Observability** | ✅ Strukturaviy JSON logging + `request_id` middleware |
| Mobil | Mobil klient (API allaqachon shunga mo'ljallangan) |
| Beta | Cheklangan kategoriya + Toshkent, real pul, kichik hajm |

**Real-time / Handover / Notifications / Anti-fraud / Nizolar / Logging / Sotuvchi reytingi
/ WS auth / Push abstraksiyasi ✅ MVP darajasida.**

## Xavfsizlik backlog (code+security review'dan, hali ochiq)

Katta review'da topilib **tuzatilgan**: forgot-password token leak, capture/release
FOR UPDATE, xaridor self-release, hold idempotency IDOR, dispute decision+lock,
webhook secret prod guard, order state machine, proxy tie-break, WS auth.

**Hali ochiq (keyingi qattiqlashtirish):**
- [ ] Token bekor qilish in-memory (`_REVOKED_TOKEN_IDS`) — restart/multi-worker'da
      yo'qoladi. Redis blacklist kerak.
- [ ] Fayl yuklash: MIME/kengaytma oq ro'yxati + hajm limiti (SVG/HTML stored XSS xatari).
- [ ] Rate limit: register/reset-password'ga ham (hozir login/bid/forgot-password).
      Reverse proxy ortida `X-Forwarded-For` parse qilish.
- [ ] `close_auction` end_time tekshiruvi — sotuvchi manual close'da muddatdan oldin
      yopa oladi (auto-closer to'g'ri; manual yo'l qattiqlashtirilsin).
- [ ] Webhook event -> payment holati ulash (`provider_event_id` dedup + `is_fresh`).
- [ ] `Payment.held_at/released_at` timezone-aware ustunga o'tkazish.
- [ ] WS avto-broadcast (sync bid -> async loop ko'prigi), SMS/push real adapteri,
      Redis fan-out, real PSP adapteri, yurist xulosasi.

## Qat'iy tartib qoidasi

Fazalar **ketma-ket**. Sabab:
- Faza C (atomik bid) Faza A'siz **sinab bo'lmaydi** — SQLite `FOR UPDATE`ni indamay yutadi,
  test yashil bo'ladi, prod'da ma'lumot buziladi.
- Faza D (escrow) Faza B'siz — Numeric/int aralashmasi pul hisobida xatoga olib keladi.
- Real-time Faza C'siz — noto'g'ri narxni tez tarqatishdan boshqa foyda yo'q.

Yangi feature Faza A–D tugamasdan qo'shilmaydi.
