# Auksion dvigateli

Bu — mahsulotning yuragi. Bu yerdagi xato = noto'g'ri g'olib = ishonch yo'qolishi.
Kod: `app/services/bid_service.py`, `app/services/auction_service.py`,
`app/repositories/bid_repository.py`.

## 1. Holat: nima BOR, nima YO'Q

| Element | Holat | Joy |
|---|---|---|
| Anti-sniping (soft close) | **BOR**, ishlaydi, testi bor | `bid_service.py:86-97` |
| Shill taqiqi (sotuvchi o'z lotiga bid) | **BOR** | `bid_service.py:56-60` |
| Min qadam tekshiruvi | **BOR** | `bid_service.py:79-84` |
| Deadline tekshiruvi | **BOR** | `bid_service.py:67-77` |
| `scheduled → active` avto-aktivatsiya | **BOR** (lekin faqat bid kelganda) | `auction_service.py:49-59` |
| Reserve tekshiruvi | **BOR** | `auction_service.py:78-85` |
| **Bid atomikligi (`FOR UPDATE`)** | **YO'Q** | butun kodda `with_for_update` yo'q |
| **Proxy bidding (max-bid)** | **YO'Q** | maydon ham yo'q |
| **Avtomatik yopish (worker)** | **YO'Q** | faqat `POST /auctions/{id}/close`, sotuvchi qo'lda |
| **State machine** | **YO'Q** | `status` to'g'ridan-to'g'ri o'zlashtiriladi |
| Race condition testi | **YO'Q** | conftest SQLite → `FOR UPDATE` sinab bo'lmaydi |

## 2. Atomik bid — MAJBURIY algoritm

**Muammo (hozir):** ikki bid parallel kelsa, ikkalasi ham `current_price = 100` ni o'qiydi,
ikkalasi ham 110 qo'yadi, ikkalasi ham qabul bo'ladi. Oxirgi yozgan yutadi. Ma'lumot buziladi.

**Yechim:** auksion qatorini tranzaksiya boshida lock qilish.

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

def place_bid(self, auction_id: int, bidder: User, payload: BidCreate) -> Bid:
    """Bidni atomik qabul qiladi.

    Auksion qatori FOR UPDATE bilan lock qilinadi: parallel bidlar navbatga
    turadi va har biri YANGILANGAN current_price ni ko'radi. Locksiz ikki bid
    bir xil narxni o'qib, ikkalasi ham qabul bo'lib qoladi.
    """
    # 1. LOCK — barcha o'qishlardan OLDIN. Butun tranzaksiya davomida ushlanadi.
    auction = self.db.execute(
        select(Auction).where(Auction.id == auction_id).with_for_update()
    ).scalar_one_or_none()
    if auction is None:
        raise HTTPException(404, "Auction not found")

    # 2. Validatsiya — endi lock ostida, ma'lumot ishonchli
    self._validate_bid(auction, bidder, payload)

    # 3. Yozish
    bid = Bid(auction_id=auction.id, bidder_id=bidder.id, amount=payload.amount)
    if auction.winning_bid is not None:
        auction.winning_bid.status = BidStatus.OUTBID
    auction.current_price = payload.amount
    auction.winning_bid = bid
    auction.highest_bidder_id = bidder.id

    # 4. Anti-sniping — hali lock ostida
    self._apply_soft_close_extension(auction)

    self.db.add_all([bid, auction])
    self.db.commit()   # lock shu yerda bo'shaydi
    self.db.refresh(bid)
    return bid
```

**Qoidalar:**
- Lock **birinchi** o'qishda olinadi. Avval o'qib, keyin lock qilish — foydasiz.
- Deadlock oldini olish: har doim **auction → bid** tartibida lock.
- Lock ushlab turganda tashqi chaqiruv (PSP, HTTP, email) **TAQIQ** — tranzaksiya cho'ziladi.
- `with_for_update(nowait=True)` ishlatmaslik: bid navbatga turishi kerak, xato qaytarmasligi.

## 3. Min qadam

```
step = max(minimum_bid_increment, tier_step(current_price))   # TIERED_BID_INCREMENT_ENABLED
minimum_next_bid = current_price + step
```
`amount < minimum_next_bid` → 400 (`BidService._min_step`, jadval: `services/bid_increment.py`).
Test muhitida jadval o'chiq — faqat sotuvchi qadami.

`AuctionRead.minimum_next_bid` — aynan shu qiymat API javobida (computed). Frontend qadam
jadvalini TAKRORLAMAYDI, shu maydonni ko'rsatadi.

Bid tarixi: `GET /auctions/{id}/bids` — ochiq, ism maskalangan (`bidder_display`),
`max_amount`/`high_bidder_max` sxemada yo'q.

## 4. Proxy bidding (max-bid) — YO'Q, qilinadi

Foydalanuvchi **max** kiritadi. Tizim uning nomidan faqat kerakli minimal miqdorda ko'taradi.

```python
def _resolve_proxy(auction: Auction, new_max: int, bidder_id: int) -> int:
    """Yangi max-bid kelganda ko'rinadigan narxni hisoblaydi.

    Qaytariladigan qiymat — OMMAVIY current_price. Yutqazgan tomonning maxi
    hech qachon oshkor qilinmaydi.
    """
    step = auction.minimum_bid_increment
    current_max = auction.high_bidder_max

    if current_max is None:
        return auction.starting_price          # birinchi bid: boshlang'ich narx

    if new_max > current_max:
        # Yangi bidder yutdi: eski maxdan bir qadam yuqori, lekin o'z maxidan oshmagan holda
        return min(new_max, current_max + step)

    if new_max == current_max:
        return current_max                     # teng — vaqt bo'yicha birinchisi yutadi

    # Yangi bidder yutqazdi: mavjud yetakchi bir qadam ko'tariladi
    return min(current_max, new_max + step)
```

**KRITIK:** `high_bidder_max` va `bids.max_amount` **hech qachon** API javobiga
(`AuctionRead`, `BidRead`, admin ro'yxatlari, WebSocket event) qo'shilmaydi.
Oshkor bo'lsa — raqib aniq bir tiyin yuqori qo'yib har doim yutadi. Bu auksionni o'ldiradi.

## 5. Anti-sniping — BOR

`bid_service.py:86-97`:

```python
seconds_until_close = (end_time - now).total_seconds()
if 0 < seconds_until_close <= settings.soft_close_window_seconds:   # 120s
    auction.end_time = end_time + timedelta(seconds=settings.soft_close_extension_seconds)  # +120s
```

Sozlamalar: `SOFT_CLOSE_WINDOW_SECONDS=120`, `SOFT_CLOSE_EXTENSION_SECONDS=120`.

**Eslatma:** metod docstring'ida "intentionally a no-op" deyilgan — bu **eskirgan**,
kod aslida ishlaydi. Tegilganda docstring tuzatilsin.

**Kelajak:** `extension_count` limiti (masalan max 20 cho'zilish) — cheksiz cho'zilishning oldini olish.

## 6. Yopish worker — YO'Q, KRITIK

Hozir: `POST /api/v1/auctions/{id}/close`, faqat **sotuvchi** chaqiradi
(`auctions.py:77-88`). Sotuvchi chaqirmasa — auksion `active` bo'lib muzlab qoladi.
Bu mahsulotning asosiy va'dasini ("majburiy deadline") **buzadi**.

Kerakli worker:

```python
async def close_expired_auctions(db: Session) -> None:
    """end_time o'tgan aktiv auksionlarni yopadi. Har 10 soniyada ishlaydi.

    Har auksion ALOHIDA tranzaksiyada yopiladi: bittasi xato bersa qolgani yopilaveradi.
    """
    now = datetime.now(UTC)
    expired_ids = db.scalars(
        select(Auction.id)
        .where(Auction.status == AuctionStatus.ACTIVE, Auction.end_time <= now)
        .order_by(Auction.end_time)
        .limit(100)
    ).all()

    for auction_id in expired_ids:
        try:
            auction = db.execute(
                select(Auction)
                .where(Auction.id == auction_id, Auction.status == AuctionStatus.ACTIVE)
                .with_for_update(skip_locked=True)   # boshqa worker olgan bo'lsa — o'tkazib yubor
            ).scalar_one_or_none()
            if auction is None:
                continue
            # Lock ostida qayta tekshir: anti-sniping end_time ni cho'zgan bo'lishi mumkin
            if _as_utc(auction.end_time) > datetime.now(UTC):
                continue
            AuctionService(db).close_auction(auction)
        except Exception:
            db.rollback()
            logger.exception("close failed", extra={"auction_id": auction_id})
```

- `skip_locked=True` — bir nechta worker instansiyasi bir auksionni ikki marta yopmasligi uchun.
- Lock ostida `end_time` **qayta** tekshiriladi: skan bilan lock orasida anti-sniping cho'zishi mumkin.
- Idempotent: allaqachon `ended` bo'lsa — hech narsa qilmaydi.
- Runner tanlovi (ARQ / APScheduler / Celery) — **ochiq**, Faza C'da hal qilinadi.

## 7. State machine — YO'Q, qilinadi

Ruxsat etilgan o'tishlar (`AuctionStatus`):

```
scheduled ──► active ──► ended
     │           │
     │           ├──► reserve_not_met
     │           └──► cancelled (faqat admin)
     └──► cancelled
```

**TAQIQ:** `ended → active`, `ended → ended`, `cancelled → *`, `reserve_not_met → active`.

```python
_ALLOWED: dict[AuctionStatus, frozenset[AuctionStatus]] = {
    AuctionStatus.SCHEDULED: frozenset({AuctionStatus.ACTIVE, AuctionStatus.CANCELLED}),
    AuctionStatus.ACTIVE: frozenset({
        AuctionStatus.ENDED, AuctionStatus.RESERVE_NOT_MET, AuctionStatus.CANCELLED
    }),
    AuctionStatus.ENDED: frozenset(),
    AuctionStatus.RESERVE_NOT_MET: frozenset(),
    AuctionStatus.CANCELLED: frozenset(),
}

def transition(auction: Auction, new: AuctionStatus) -> None:
    """Auksion holatini FAQAT shu funksiya o'zgartiradi.

    To'g'ridan-to'g'ri auction.status = ... yozish TAQIQ: bu yerda audit,
    tekshiruv va yon effektlar (order yaratish, xabarnoma) markazlashgan.
    """
    if new not in _ALLOWED[auction.status]:
        raise InvalidTransition(f"{auction.status} → {new} taqiqlangan")
    auction.status = new
```

**Muammo (hozir):** `PATCH /api/v1/auctions/{id}/status` sotuvchiga **istalgan** holatni
o'rnatishga ruxsat beradi (`auctions.py:61-74`) — hech qanday tekshiruvsiz. Sotuvchi yutqazayotgan
auksionni `cancelled` qilib qo'yishi mumkin. Bu endpoint state machine bilan qattiq cheklanishi kerak.

## 8. Majburiy testlar

| Test | Nega |
|---|---|
| Parallel 2 bid, bir xil narx → faqat bittasi yutadi | Atomiklikning yagona haqiqiy isboti |
| N=50 parallel bid → `current_price` = eng yuqorisi, bidlar soni to'g'ri | Yuk ostida yaxlitlik |
| Anti-sniping: 119s qolganda bid → `end_time` +120s | BOR (`test_bids.py`) |
| Anti-sniping: 300s qolganda bid → `end_time` o'zgarmaydi | Chegara |
| Proxy: A max=100, B max=80 → narx 85, A yetakchi | Proxy mantiq |
| Proxy: API javobida `high_bidder_max` YO'Q | Maxfiylik — regressiya qalqoni |
| Sotuvchi o'z lotiga bid → 400 | BOR |
| `end_time` o'tgan → bid 400 | BOR |
| Worker: `end_time` o'tgan auksion avtomatik `ended` | Va'da |
| Worker ikki marta ishga tushsa → bitta order | Idempotentlik |
| `ended → active` → xato | State machine |

**KRITIK:** hozir `tests/conftest.py` **SQLite in-memory** (`sqlite+pysqlite:///:memory:`) ishlatadi.
SQLite'da `FOR UPDATE` yo'q va u indamay o'tkazib yuboradi → atomiklik testi **yolg'on yashil**
beradi. Race testi yozishdan **oldin** test bazasi Postgres'ga ko'chirilishi shart (Faza A).
