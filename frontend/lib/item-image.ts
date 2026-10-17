/**
 * Tovar rasmlari — YAGONA manba.
 *
 * Backend ikkita maydon qaytaradi: `item_images` (yuklangan fayllar, `is_primary`
 * bilan) va `images` (URL ro'yxati). Ustuvorlik `item_images` da; asosiy rasm
 * birinchi bo'ladi. Har bir yo'l `mediaUrl()` orqali to'liq URL'ga aylantiriladi —
 * chunki backend `/uploads/...` ni NISBIY qaytaradi va u `/api/v1` ostida emas.
 */
import type { Item } from "@/lib/api/types"
import { mediaUrl } from "@/lib/api/client"

/** Tovarning barcha rasmlari, asosiysi birinchi. Rasm yo'q bo'lsa — bo'sh massiv. */
export function itemImageUrls(item: Item): string[] {
  const raw =
    item.item_images.length > 0
      ? [...item.item_images]
          .sort((a, b) => Number(b.is_primary) - Number(a.is_primary))
          .map((im) => im.image_url)
      : item.images
  return raw.filter(Boolean).map(mediaUrl)
}

/** Ro'yxat/karta uchun bitta asosiy rasm. Rasm yo'q bo'lsa — null. */
export function heroImage(item: Item): string | null {
  return itemImageUrls(item)[0] ?? null
}
