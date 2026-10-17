"use client"

import * as React from "react"
import Link from "next/link"
import { BellIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import { unreadNotificationsCount } from "@/lib/api/engagement"

/**
 * Header uchun bildirishnoma qo'ng'irog'i.
 *
 * Faqat autentifikatsiyadan o'tgan foydalanuvchiga ko'rinadi (anonim ->
 * hech narsa render qilinmaydi — header uni sahifada joylashtiradi).
 * O'qilmagan sonini backend'dan oladi va nishoncha ko'rsatadi.
 */
function NotificationBell({ className }: { className?: string }) {
  const status = useAuthStore((s) => s.status)
  const authed = status === "authenticated"
  const [unread, setUnread] = React.useState(0)

  React.useEffect(() => {
    // Anonim holatda komponent null render qiladi — sonni yangilash shart emas.
    if (!authed) return
    let alive = true
    unreadNotificationsCount()
      .then((count) => {
        if (alive) setUnread(count)
      })
      .catch(() => {
        // Sonini olib bo'lmasa — nishonchasiz qo'ng'iroq ko'rsatamiz.
        if (alive) setUnread(0)
      })
    return () => {
      alive = false
    }
  }, [authed])

  // Anonim yoki holat aniqlanmagan bo'lsa — qo'ng'iroq ko'rsatilmaydi.
  if (!authed) return null

  const hasUnread = unread > 0
  const badgeText = unread > 99 ? "99+" : String(unread)

  return (
    <Link
      href="/notifications"
      aria-label={
        hasUnread
          ? `Bildirishnomalar, ${unread} ta oʻqilmagan`
          : "Bildirishnomalar"
      }
      className={cn(
        "relative inline-flex size-10 items-center justify-center rounded-lg text-foreground outline-none transition-colors hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
        className
      )}
    >
      <BellIcon className="size-5" aria-hidden="true" />
      {hasUnread && (
        <span
          className="absolute top-0.5 right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-xs font-semibold text-destructive-foreground tabular-nums"
          aria-hidden="true"
        >
          {badgeText}
        </span>
      )}
    </Link>
  )
}

export { NotificationBell }
