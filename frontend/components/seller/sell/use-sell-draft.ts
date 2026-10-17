"use client"

import * as React from "react"

/**
 * Forma qoralamasini brauzerda saqlaydi — sahifa yangilansa yoki tasodifan yopilsa
 * kiritilgan matn yo'qolmasin. Faqat shu brauzer uchun qulaylik: serverga ketmaydi,
 * rasmlar (File) saqlanmaydi. localStorage bloklangan bo'lsa jim ishlamaydi.
 */
const VERSION = 1
const SAVE_DELAY_MS = 600

function storageKey(userId: number): string {
  return `bazart:sell-draft:v${VERSION}:${userId}`
}

function readDraft<T>(userId: number): T | null {
  try {
    const raw = window.localStorage.getItem(storageKey(userId))
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

function writeDraft<T>(userId: number, value: T): void {
  try {
    window.localStorage.setItem(storageKey(userId), JSON.stringify(value))
  } catch {
    // Saqlash imkoni yo'q (maxfiy rejim, kvota) — forma baribir ishlaydi.
  }
}

function removeDraft(userId: number): void {
  try {
    window.localStorage.removeItem(storageKey(userId))
  } catch {
    // e'tiborsiz
  }
}

function useSellDraft<T>(userId: number | undefined) {
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  React.useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    []
  )

  const load = React.useCallback((): T | null => {
    if (userId == null) return null
    return readDraft<T>(userId)
  }, [userId])

  const save = React.useCallback(
    (value: T) => {
      if (userId == null) return
      if (timer.current) clearTimeout(timer.current)
      timer.current = setTimeout(() => writeDraft(userId, value), SAVE_DELAY_MS)
    },
    [userId]
  )

  const clear = React.useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    if (userId != null) removeDraft(userId)
  }, [userId])

  return React.useMemo(() => ({ load, save, clear }), [load, save, clear])
}

/** Birinchi render uchun sinxron o'qish (forma faqat brauzerda, kirgandan keyin chiziladi). */
function loadSellDraft<T>(userId: number | undefined): T | null {
  if (userId == null || typeof window === "undefined") return null
  return readDraft<T>(userId)
}

export { useSellDraft, loadSellDraft }
