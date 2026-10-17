# Bazart — Dizayn tizimi

Frontend (`frontend/`) dizayn qarorlari. Yo'naltiruvchi tamoyil: **fotolar — qahramon,
interfeys — sahna**. Chrome neytral bo'lib orqaga chekinadi; yagona aksent faqat harakat va
shoshilinchlikni bildiradi. Har sahifaning bitta vazifasi bor.

Auditoriya: telefondan xarid qiluvchi 20–45 yoshli xaridorlar (O'zbekiston, narx so'mda, til o'zbekcha).

## 1. Palitra

Manba: `frontend/app/globals.css` (`:root` va `.dark`). Kontrastlar WCAG AA bo'yicha hisoblab
tekshirilgan. **Komponentlarda hardcode rang TAQIQ** — faqat token.

| Rol | Token | Yorug' | Qorong'u | Kontrast (AA) |
|---|---|---|---|---|
| Asos (sahifa foni) | `--background` | `#F7F6F4` | `#171614` | matn 16.1:1 / 16.3:1 |
| Sirt (karta/bar) | `--card` `--popover` | `#FFFFFF` | `#1E1D1B` | — |
| Matn 1-daraja | `--foreground` | `#1B1A18` | `#F4F3F0` | 16.1:1 |
| Matn 2-daraja | `--muted-foreground` | `#6B6863` | `#A8A49D` | 5.14:1 / 7.29:1 |
| Brend aksenti | `--brand` `--primary` | `#12659E` | `#1F72AD` | oq matn 6.21:1 / 5.16:1 |
| Success | `--success` | `#0E7A46` | `#0E7A46` | oq matn 5.4:1 |
| Warning | `--warning` | `#E1900B` | `#F0A420` | **quyuq matn** 6.79:1 / 8.64:1 |
| Error | `--error` | `#C4362C` | `#C4362C` | oq matn 5.37:1 |

Chegara: `--border #E7E4DF` (dark: `oklch(1 0 0 / 10%)`).

**Nega majolika ko'ki:** marketplace fotolari (kiyim, elektronika, mebel) iliq va to'yingan —
ranglar oldinga intiladi. Sovuq, o'rta-to'yingan ko'k kompozitsion jihatdan orqaga chekinadi,
tovar rasmi bilan raqobatlashmaydi, ammo CTA/faol holatda aniq ko'rinadi. Yashil "success",
qizil/amber "urgency" bilan band — shu sabab brend ko'k bo'lishi funksional jihatdan to'g'ri.
Ildizi — Samarqand/Buxoro koshin an'anasi.

## 2. Tipografika

Ikki rol, ikkalasi Google Fonts, `next/font` orqali (`frontend/app/layout.tsx`).

- **Sarlavha:** Space Grotesk (600/700) — `font-heading`. O'ziga xos `a`/`g` shakllari.
- **Matn/UI:** Inter (400/500/600) — `font-sans`. 360px'da tiniq; `tabular-nums` bilan narxlar tekis.
- Narx/countdown raqamlari Inter `tabular-nums` — alohida uchinchi shrift yo'q.

**oʻ/gʻ (U+02BB) qamrovi tekshirilgan** — bu tanlovni belgiladi. Ko'p zamonaviy shriftlar bu
belgini qamramaydi va tofu ko'rsatadi:

| Shrift | U+02BB (oʻ/gʻ) | Holat |
|---|---|---|
| Space Grotesk, Inter | ✓ | **Tanlandi** |
| IBM Plex Sans, Work Sans | ✓ | zaxira |
| Manrope, Plus Jakarta Sans, Sora, Figtree, Onest | ✗ | **rad** (tofu) |

Type scale: **12 / 14 / 16 / 18 / 24 / 32 / 48px** (`text-xs`…`text-3xl`). Boshqa o'lcham yo'q.
Spacing 4px asosida. Sarlavha faqat 24/32/48, matn 14/16/18.

## 3. Layout kontseptsiyasi (mobil-birinchi, 360–1440px)

- **Asosiy sahifa** — *vazifa: tez qidirish + shoshilinchni ko'rsatish.* Katta qidiruv →
  kategoriya chip'lari → **"Bugun tugaydi"** rail (deadline bo'yicha saralangan, sahifaning
  umurtqasi) → yangi e'lonlar grid. Pastda tab-bar.
- **Katalog** — *vazifa: natijalarni saralab skan qilish.* Sticky filtr/sort bar (default sort:
  tugash vaqti) → 2 ustunli grid (desktop 3–4 + yon filtr). Har kartada muddat chizig'i + narx +
  taklif soni.
- **Mahsulot** — *vazifa: ishonch bilan taklif berish.* Hero foto + muddat chizig'i → sarlavha →
  katta joriy narx (tabular) + keyingi qadam → sotuvchi reytingi + escrow himoyasi → tavsif →
  sticky asosiy CTA (accent). Desktop: foto chapda, narx/CTA o'ngda yopishqoq ustun.

## 4. Imzo element — "Muddat chizig'i" (Deadline bar)

Platformani ajratib turadigan yagona detal: **har tovar rasmining pastki chetiga o'rnatilgan
ingichka vaqt-o'lchagich + tabular countdown**. Kartada ham, hero'da ham bir xil komponent.
Deadline yaqinlashgani sari kuchayadi:

| Qolgan vaqt | Rang | Holat |
|---|---|---|
| > 24 soat | `--muted-foreground` (neytral) | xotirjam |
| ≤ 6 soat | `--warning` (amber) | diqqat |
| ≤ 30 daqiqa | `--error` (qizil) | shoshilinch |

- Bazart'ning yagona farqi — majburiy deadline. Imzo shu farqni ko'zga aylantiradi.
- Rasm **chetida**, yarim-shaffof scrim ustida — fotoni yopmaydi, u bilan raqobatlashmaydi.
- Motion: faqat raqam jonli yangilanadi (dekorativ sikl yo'q); `prefers-reduced-motion` mos.
- CLAUDE.md dagi taqiqlangan shablonlarning hech biri emas. Egalik — izchillik + eskalatsiya orqali.

## Motion

Faqat 150–250ms funksional o'tishlar (`--duration-fast/base/slow`, `--ease-standard`).
Dekorativ scroll-animatsiya va parallax TAQIQ. `prefers-reduced-motion` globals.css da reset qilingan.

## Terminologiya (UI matni)

Sotiladigan narsa foydalanuvchiga **"mahsulot"** deb ataladi — **"lot" EMAS** (mahsulotlarim,
mahsulotingiz sotildi, Mahsulot joylash). Bu faqat foydalanuvchiga ko'rinadigan matnga tegishli:
kod nomlari (`Lot` turi, `components/lot/*`, `/lot/[id]` marshruti) hozircha o'zgarmaydi.
