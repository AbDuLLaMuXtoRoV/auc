"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { toast } from "sonner"
import { HeartIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { ApiError } from "@/lib/api/client"
import { listWatchlist, addToWatchlist, removeFromWatchlist } from "@/lib/api/watchlist"
import { useAuthStore } from "@/lib/store/auth"
import { Button } from "@/components/ui/button"

/**
 * "Kuzatish" tugmasi. Holat optimistik almashadi — server rad etsa
 * avvalgi holatga qaytamiz va xatoni ko'rsatamiz.
 */
function WatchButton({
  auctionId,
  className,
}: {
  auctionId: number
  className?: string
}) {
  const status = useAuthStore((s) => s.status)
  const pathname = usePathname()

  // null — hali yuklanmoqda.
  const [watching, setWatching] = React.useState<boolean | null>(null)
  const [busy, setBusy] = React.useState(false)

  React.useEffect(() => {
    if (status !== "authenticated") return
    let alive = true
    listWatchlist()
      .then((list) => {
        if (alive) setWatching(list.some((w) => w.auction_id === auctionId))
      })
      .catch(() => {
        // Ro'yxat yuklanmasa ham tugma ishlaydi — "kuzatilmagan" deb boshlaymiz.
        if (alive) setWatching(false)
      })
    return () => {
      alive = false
    }
  }, [status, auctionId])

  if (status === "anonymous") {
    return (
      <Button asChild variant="outline" size="md" className={className}>
        <Link href={`/login?next=${encodeURIComponent(pathname)}`}>
          <HeartIcon aria-hidden="true" />
          Kuzatish
        </Link>
      </Button>
    )
  }

  const toggle = async () => {
    if (busy || watching === null) return
    const prev = watching
    setWatching(!prev)
    setBusy(true)
    try {
      if (prev) await removeFromWatchlist(auctionId)
      else await addToWatchlist(auctionId)
    } catch (e) {
      setWatching(prev)
      toast.error(
        e instanceof ApiError ? e.detail : "Kuzatuv roʻyxatini yangilab boʻlmadi."
      )
    } finally {
      setBusy(false)
    }
  }

  const on = watching === true

  return (
    <Button
      variant="outline"
      size="md"
      aria-pressed={on}
      loading={watching === null}
      disabled={busy}
      onClick={toggle}
      className={cn(on && "border-primary/40 text-primary", className)}
    >
      {watching !== null && (
        <HeartIcon className={cn(on && "fill-current")} aria-hidden="true" />
      )}
      {on ? "Kuzatilmoqda" : "Kuzatish"}
    </Button>
  )
}

export { WatchButton }
