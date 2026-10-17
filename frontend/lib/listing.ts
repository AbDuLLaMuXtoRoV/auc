/**
 * Mahsulot joylash qoidalari — forma va mahsulot sahifasi bir xil manbadan foydalanadi.
 *
 * Kategoriya bo'yicha profil `slug` orqali bog'lanadi (id baza holatiga bog'liq,
 * slug esa barqaror). Bazada profili yo'q kategoriya `DEFAULT_PROFILE` ni oladi.
 */

/** "Nuqsonlari yoʻq" belgisi tanlanganda `defects` maydoniga yoziladigan matn. */
export const NO_DEFECTS_TEXT = "Nuqsonlari yoʻq"

/** Server limiti: `settings.max_images_per_item`. */
export const MAX_IMAGES = 10
/** Server limiti: `settings.upload_max_bytes` (5 000 000 bayt). */
export const MAX_IMAGE_BYTES = 5_000_000
/** Server oq ro'yxati: `storage_service.ALLOWED_CONTENT_TYPES`. */
export const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]

export const DESCRIPTION_MAX = 5000

export type CategoryProfile = {
  /** Ishlab chiqarilgan yil mazmunli bo'lgan kategoriyalar (avto, texnika). */
  showYear: boolean
  /** Komplektatsiya chiplari. */
  equipment: string[]
  /** Tavsifga nimalarni yozish kerakligi — sotuvchiga eslatma. */
  descriptionHint: string
}

const DEFAULT_PROFILE: CategoryProfile = {
  showYear: false,
  equipment: ["Quti", "Hujjatlar", "Kafolat taloni", "Chek"],
  descriptionHint: "Oʻlchami, rangi, qachon va qayerdan olingani, nima uchun sotilayotgani.",
}

const PROFILES: Record<string, CategoryProfile> = {
  telefonlar: {
    showYear: true,
    equipment: ["Quti", "Zaryadlovchi", "Kabel", "Quloqchin", "Gʻilof", "Kafolat taloni", "Chek"],
    descriptionHint:
      "Xotira hajmi, batareya holati (%), IMEI, rangi, taʼmirlanganmi, ekranda tirnalish bormi.",
  },
  elektronika: {
    showYear: true,
    equipment: ["Quti", "Quvvat bloki", "Kabel", "Pult", "Kafolat taloni", "Chek", "Hujjatlar"],
    descriptionHint: "Modeli, xususiyatlari (protsessor, xotira, ekran), ishlatilgan muddati, taʼmir tarixi.",
  },
  avto: {
    showYear: true,
    equipment: ["Texpasport", "Ikkinchi kalit", "Servis kitobchasi", "Qishki shinalar", "Hujjatlar"],
    descriptionHint:
      "Yurgan masofasi (km), dvigatel hajmi, uzatmalar qutisi, rangi, boʻyalgan qismlari, avariya tarixi.",
  },
  kiyim: {
    showYear: false,
    equipment: ["Yorliq", "Quti", "Chek"],
    descriptionHint: "Oʻlchami, materiali, brendi, necha marta kiyilgan.",
  },
  kitoblar: {
    showYear: false,
    equipment: [],
    descriptionHint: "Muallifi, nashr yili, tili, sahifalar holati.",
  },
  sport: {
    showYear: false,
    equipment: ["Quti", "Hujjatlar", "Chek"],
    descriptionHint: "Oʻlchami yoki ogʻirligi, brendi, ishlatilgan muddati.",
  },
  bolalar: {
    showYear: false,
    equipment: ["Quti", "Hujjatlar", "Chek"],
    descriptionHint: "Qaysi yoshga moʻljallangan, brendi, toʻliq butligi.",
  },
  uy: {
    showYear: false,
    equipment: ["Quti", "Hujjatlar", "Kafolat taloni", "Chek"],
    descriptionHint: "Oʻlchami, materiali, brendi, ishlatilgan muddati.",
  },
}

export function categoryProfile(slug: string | undefined): CategoryProfile {
  return (slug && PROFILES[slug]) || DEFAULT_PROFILE
}

/**
 * Nom bo'yicha kategoriya taklifi uchun kalit so'zlar (kichik harf, lotin va kirill).
 * Ikki daraja: avval TUR so'zlari (televizor, divan), keyin BREND so'zlari —
 * "Samsung televizor" telefonga emas, elektronikaga tushsin. So'z boshidan moslik
 * tekshiriladi: "iphone" "iPhone 13 Pro" ni topadi.
 */
const TYPE_KEYWORDS: Record<string, string[]> = {
  telefonlar: ["telefon", "smartfon", "телефон", "смартфон"],
  elektronika: [
    "noutbuk", "laptop", "kompyuter", "monitor", "planshet", "televizor", "playstation",
    "pristavka", "quloqchin", "kolonka", "kamera", "fotoapparat", "printer", "router",
    "smart soat", "ноутбук", "компьютер", "планшет", "телевизор", "наушники",
  ],
  avto: [
    "mashina", "avtomobil", "shina", "balon", "akkumulyator", "машина", "шины", "диски",
  ],
  kiyim: [
    "ko'ylak", "kurtka", "palto", "shim", "jinsi", "futbolka", "libos", "kostyum",
    "krossovka", "poyabzal", "tufli", "etik", "sumka", "куртка", "платье", "кроссовки",
  ],
  kitoblar: ["kitob", "roman", "darslik", "lug'at", "entsiklopediya", "книга"],
  sport: [
    "velosiped", "samokat", "gantel", "trenajor", "shtanga", "boks", "koptok", "to'p",
    "chang'i", "велосипед", "тренажер",
  ],
  bolalar: [
    "kolyaska", "aravacha", "beshik", "o'yinchoq", "bolalar", "chaqaloq", "коляска", "игрушка",
  ],
  uy: [
    "lagan", "kosa", "choynak", "idish", "divan", "stol", "stul", "kreslo", "shkaf", "karavot",
    "gilam", "parda", "muzlatgich", "kir yuvish", "changyutgich", "konditsioner", "mebel",
    "диван", "холодильник", "ковер",
  ],
}

const BRAND_KEYWORDS: Record<string, string[]> = {
  telefonlar: [
    "iphone", "samsung", "galaxy", "redmi", "xiaomi", "poco", "honor", "huawei", "pixel",
    "nokia", "realme", "oppo", "vivo", "infinix", "tecno", "айфон", "самсунг",
  ],
  elektronika: [
    "macbook", "ipad", "ps4", "ps5", "xbox", "nintendo", "airpods", "jbl", "canon", "nikon",
    "sony", "lenovo", "asus", "acer",
  ],
  avto: [
    "chevrolet", "cobalt", "nexia", "gentra", "lacetti", "malibu", "spark", "damas", "matiz",
    "tracker", "captiva", "byd", "kia", "hyundai", "toyota", "mercedes", "bmw", "lada",
  ],
  kiyim: ["nike", "adidas", "puma", "zara"],
  bolalar: ["lego"],
}

function normalizeApostrophes(text: string): string {
  return text.replace(/[ʻʼ`’]/g, "'")
}

/** `phrases` — faqat ko'p so'zli kalitlar ("kir yuvish"), aks holda faqat bitta so'zlilar. */
function findIn(
  table: Record<string, string[]>,
  text: string,
  words: string[],
  phrases: boolean
): string | undefined {
  for (const [slug, keywords] of Object.entries(table)) {
    for (const key of keywords) {
      const isPhrase = key.includes(" ")
      if (isPhrase !== phrases) continue
      if (isPhrase ? text.includes(key) : words.some((w) => w.startsWith(key))) return slug
    }
  }
  return undefined
}

/** Nomdan kategoriya slug'ini taxmin qiladi; topilmasa undefined. */
export function suggestCategorySlug(title: string): string | undefined {
  const text = normalizeApostrophes(title.toLowerCase())
  if (text.trim().length < 3) return undefined
  const words = text.split(/[\s,.:;!?\-/()]+/).filter(Boolean)
  // Ko'p so'zli ibora aniqroq: "kir yuvish mashinasi" avtoga emas, uy jihoziga tushadi.
  return (
    findIn(TYPE_KEYWORDS, text, words, true) ??
    findIn(TYPE_KEYWORDS, text, words, false) ??
    findIn(BRAND_KEYWORDS, text, words, false)
  )
}

/**
 * Avtomatik minimal qadam (so'm): boshlang'ich narxning 5%, 1 000 so'mga yuqoriga
 * yaxlitlangan. Server qadam jadvali baribir kattarog'ini qo'llaydi.
 */
export function autoIncrementSoum(startingSoum: number): number {
  if (!(startingSoum > 0)) return 0
  return Math.max(1000, Math.ceil((startingSoum * 0.05) / 1000) * 1000)
}

const endsAtFormatter = new Intl.DateTimeFormat("uz-UZ", {
  timeZone: "Asia/Tashkent",
  day: "numeric",
  month: "long",
  hour: "2-digit",
  minute: "2-digit",
})

/** "18-oktabr, 21:00" — auksion tugash vaqti (Toshkent vaqti). */
export function formatEndsAt(nowMs: number, days: number): string {
  return endsAtFormatter.format(new Date(nowMs + days * 24 * 60 * 60 * 1000))
}
