/**
 * Xabar UI yordamchilari — sana formatlash va suhbat tomonini aniqlash.
 * `now` talab qilmaydigan absolyut format (render vaqtida xavfsiz).
 */
import type { Conversation } from "@/lib/api/messages"

const dateTimeFormatter = new Intl.DateTimeFormat("uz-UZ", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
})

const timeFormatter = new Intl.DateTimeFormat("uz-UZ", {
  hour: "2-digit",
  minute: "2-digit",
})

/** "5-avg, 14:30" — absolyut sana+vaqt. */
export function formatMessageDateTime(iso: string): string {
  const t = Date.parse(iso)
  if (!Number.isFinite(t)) return ""
  return dateTimeFormatter.format(new Date(t))
}

/** "14:30" — faqat vaqt (xabar puufakchasi uchun). */
export function formatMessageTime(iso: string): string {
  const t = Date.parse(iso)
  if (!Number.isFinite(t)) return ""
  return timeFormatter.format(new Date(t))
}

/**
 * Joriy foydalanuvchi nuqtai nazaridan qarshi tomon roli.
 * Backend suhbatda faqat buyer_id/seller_id beradi (ism yo'q) — shuning uchun
 * rol bo'yicha yorliq ko'rsatamiz.
 */
export function counterpartyLabel(conv: Conversation, userId: number | null): string {
  if (userId != null && userId === conv.seller_id) return "Xaridor"
  return "Sotuvchi"
}
