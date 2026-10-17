import type { DisputeReason, DisputeStatus } from "@/lib/api/engagement"

/** Nizo sababi — o'zbekcha yorliq (DisputeReason tartibida). */
export const DISPUTE_REASON_LABEL: Record<DisputeReason, string> = {
  not_received: "Tovar kelmadi",
  not_as_described: "Taʼrifga mos emas",
  damaged: "Shikastlangan holatda keldi",
  fake: "Soxta / asl emas",
  other: "Boshqa sabab",
}

/** Nizo sabablari ro'yxati (forma tartibida). */
export const DISPUTE_REASONS: DisputeReason[] = [
  "not_received",
  "not_as_described",
  "damaged",
  "fake",
  "other",
]

/** Nizo holati — o'zbekcha yorliq. */
export const DISPUTE_STATUS_LABEL: Record<DisputeStatus, string> = {
  open: "Ochiq",
  under_review: "Koʻrib chiqilmoqda",
  resolved_buyer: "Xaridor foydasiga hal qilindi",
  resolved_seller: "Sotuvchi foydasiga hal qilindi",
}
