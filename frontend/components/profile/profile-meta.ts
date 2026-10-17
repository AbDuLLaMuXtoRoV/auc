/**
 * Profil UI yordamchilari — absolyut sana formatlash (uz-UZ).
 * `now` talab qilmaydi — render vaqtida xavfsiz.
 */

const dateFormatter = new Intl.DateTimeFormat("uz-UZ", {
  day: "numeric",
  month: "long",
  year: "numeric",
})

/** "5-avgust 2026" — absolyut sana. Yaroqsiz ISO uchun bo'sh string. */
export function formatProfileDate(iso: string): string {
  const t = Date.parse(iso)
  if (!Number.isFinite(t)) return ""
  return dateFormatter.format(new Date(t))
}
