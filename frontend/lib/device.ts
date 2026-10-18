/**
 * Telefon holati: daraja, batareya va nosozliklar matnlari — bitta manba
 * (sotish formasi, kartochka, lot sahifasi, narxlar sahifasi bir xil gapirsin).
 * Mezonlar narx ko'rsatkichi manba jadvalidan (backend `price_guide_service`).
 */

import type { DeviceDefect, DeviceGrade } from "@/lib/api/types"

export const GRADES: DeviceGrade[] = ["a", "a_minus", "b_plus", "b_minus"]

export const GRADE_INFO: Record<
  DeviceGrade,
  { short: string; label: string; description: string; batteryMin: number }
> = {
  a: {
    short: "A",
    label: "Aʼlo",
    description: "Tirnalish va urilish yoʻq, kamera butun, ekranda iz qolmagan.",
    batteryMin: 90,
  },
  a_minus: {
    short: "A-",
    label: "Juda yaxshi",
    description: "Faqat mayda tirnalishlar, urilish yoʻq, kamera butun.",
    batteryMin: 90,
  },
  b_plus: {
    short: "B+",
    label: "Yaxshi",
    description: "Ekranda mayda tirnalish, chetida 1–2 ta yengil urilish.",
    batteryMin: 85,
  },
  b_minus: {
    short: "B-",
    label: "Oʻrtacha",
    description: "Ekranda yengil tirnalishlar, chetida 2–3 ta yengil urilish.",
    batteryMin: 81,
  },
}

export const DEFECTS: DeviceDefect[] = [
  "screen_broken",
  "lcd",
  "face_id",
  "camera",
  "back_glass",
  "wifi",
  "mic",
  "true_tone",
  "genuine_parts",
  "nongenuine_parts",
]

export const DEFECT_LABEL: Record<DeviceDefect, string> = {
  screen_broken: "Ekran oynasi singan",
  lcd: "Displey nosoz (dogʻ, chiziq, rang)",
  face_id: "Face ID / Touch ID ishlamaydi",
  camera: "Kamera nosoz",
  back_glass: "Orqa oyna singan",
  wifi: "Wi-Fi yoki kompas nosoz",
  mic: "Mikrofon ishlamaydi",
  true_tone: "True Tone ishlamaydi",
  genuine_parts: "«Original qism» xabari (qism almashtirilgan)",
  nongenuine_parts: "«Original boʻlmagan qism» xabari",
}

/** Badge varianti: yuqori daraja — yashil, past — neytral (rang faqat token orqali). */
export function gradeVariant(grade: DeviceGrade): "success" | "secondary" | "outline" {
  if (grade === "a" || grade === "a_minus") return "success"
  if (grade === "b_plus") return "secondary"
  return "outline"
}

/** "8.55 soʻm" — kurs (1 won necha tiyin) ni oʻqiladigan matnga. */
export function formatRate(rateTiyinPerKrw: number): string {
  return `${(rateTiyinPerKrw / 100).toFixed(2)} soʻm`
}

/** "+15%" / "−5%" / "" (tuzatma yoʻq). */
export function formatAdjust(bps: number): string {
  if (bps === 0) return ""
  const pct = (Math.abs(bps) / 100).toFixed(bps % 100 === 0 ? 0 : 1)
  return `${bps > 0 ? "+" : "−"}${pct}%`
}
