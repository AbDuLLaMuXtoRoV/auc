/**
 * Sotuvchi (listing yaratish) oqimi uchun API funksiyalari.
 *
 * Pul maydonlari — TIYIN (string). soʻm kiritilsa `soumToTiyin` bilan aylantiring.
 * Rasm yuklash multipart/form-data orqali — bu holda `apiFetch` emas, toʻgʻridan-toʻgʻri
 * `fetch` ishlatiladi (Content-Type'ni brauzer boundary bilan oʻzi qoʻyadi).
 */

import { apiFetch, API_BASE, ApiError } from "@/lib/api/client";
import { getAccessToken } from "@/lib/api/token";
import type { Item, ItemImage, Auction, ItemCondition } from "@/lib/api/types";

export type CreateItemPayload = {
  title: string;
  description?: string;
  category_id?: number;
  condition: ItemCondition;
  /** Erkin matnli aniq manzil (koʻcha, moʻljal). */
  location?: string;
  /** Ishlab chiqarilgan yil, 1900–2100. */
  year?: number;
  /** Komplektatsiya, koʻpi 2000 belgi. */
  equipment?: string;
  /** Nuqsonlar, koʻpi 2000 belgi. */
  defects?: string;
  /** Video havola (http/https), koʻpi 500 belgi. */
  video_url?: string;
  /** Viloyat — GET /regions dan. */
  region_id?: number;
  /** Tuman — tanlangan viloyatning GET /regions/{id}/districts roʻyxatidan. */
  district_id?: number;
  /** tiyin (string) */
  starting_price: string;
  /** tiyin (string) */
  reserve_price?: string;
};

/** Tovar (item) yaratish. POST /items → Item. */
export function createItem(payload: CreateItemPayload): Promise<Item> {
  return apiFetch<Item>("/items", { method: "POST", body: payload });
}

/**
 * Tovarga rasm yuklash. POST /items/{id}/images (multipart).
 * FormData ishlatilgani uchun Content-Type qoʻlda qoʻyilmaydi — brauzer
 * multipart boundary bilan avtomatik qoʻyadi. Bearer qoʻlda qoʻshiladi.
 */
export async function uploadItemImage(
  itemId: number,
  file: File,
  isPrimary: boolean
): Promise<ItemImage> {
  const form = new FormData();
  form.append("file", file);
  form.append("is_primary", isPrimary ? "true" : "false");

  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/items/${itemId}/images`, {
      method: "POST",
      headers,
      body: form,
    });
  } catch {
    throw new ApiError(0, "Serverga ulanib boʻlmadi. Backend ishga tushganini tekshiring.");
  }

  if (!res.ok) {
    let detail = res.statusText || "Rasm yuklanmadi";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail))
        detail = data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(", ");
    } catch {
      // JSON emas — statusText qoladi.
    }
    throw new ApiError(res.status, detail);
  }

  // Backend {"image": ItemImage} qaytaradi.
  const data = (await res.json()) as { image: ItemImage };
  return data.image;
}

export type CreateAuctionPayload = {
  item_id: number;
  /** ISO datetime */
  start_time: string;
  duration_days: 3 | 5 | 7;
  /** tiyin (string) */
  minimum_bid_increment: string;
  /** tiyin (string) */
  reserve_price?: string;
};

/** Auksion ochish. POST /auctions → Auction. duration_days beriladi (end_time EMAS). */
export function createAuction(payload: CreateAuctionPayload): Promise<Auction> {
  return apiFetch<Auction>("/auctions", { method: "POST", body: payload });
}

/** Sotuvchining tovarlari. GET /items?seller_id={id} → Item[]. */
export function listSellerItems(sellerId: number): Promise<Item[]> {
  const q = new URLSearchParams();
  q.set("seller_id", String(sellerId));
  q.set("limit", "100");
  return apiFetch<Item[]>(`/items?${q.toString()}`, { auth: false });
}
