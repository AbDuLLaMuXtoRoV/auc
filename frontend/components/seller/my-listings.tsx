"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  ArrowRightIcon,
  PackageOpenIcon,
  PlusIcon,
  RotateCcwIcon,
  TriangleAlertIcon,
  XIcon,
} from "lucide-react"
import { toast } from "sonner"

import { formatTiyin } from "@/lib/format"
import type { Auction, Item, ItemStatus, ItemCondition } from "@/lib/api/types"
import { cancelListing, listSellerAuctions, listSellerItems } from "@/lib/api/seller"
import { ApiError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/store/auth"
import { ConfirmDialog } from "@/components/lot/confirm-dialog"
import { RelistDialog } from "@/components/seller/relist-dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
  EmptyContent,
} from "@/components/ui/empty"

const CONDITION_LABEL: Record<ItemCondition, string> = {
  new: "Yangi",
  used: "Ishlatilgan",
  refurbished: "Tiklangan",
}

const STATUS_LABEL: Record<ItemStatus, string> = {
  draft: "Qoralama",
  scheduled: "Rejalashtirilgan",
  pending: "Kutilmoqda",
  active: "Faol",
  sold: "Sotilgan",
  cancelled: "Bekor qilingan",
}

const STATUS_VARIANT: Record<
  ItemStatus,
  "default" | "secondary" | "success" | "warning" | "neutral" | "outline"
> = {
  draft: "secondary",
  scheduled: "secondary",
  pending: "warning",
  active: "success",
  sold: "neutral",
  cancelled: "outline",
}

/** Ikkinchi imkoniyat muddati tugashini qisqa matnga aylantiradi (Asia/Tashkent). */
function formatExpiry(iso: string): string {
  return new Intl.DateTimeFormat("uz-UZ", {
    timeZone: "Asia/Tashkent",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso))
}

function SecondChanceNotice({ auction }: { auction: Auction }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-warning bg-warning/10 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 gap-2">
        <TriangleAlertIcon className="mt-0.5 size-4 shrink-0 text-foreground" aria-hidden="true" />
        <div className="grid gap-0.5">
          <p className="text-sm font-medium text-foreground">
            Rezervga yetmadi — eng yuqori taklifga sotish mumkin
          </p>
          {auction.second_chance_expires_at && (
            <p className="text-xs text-muted-foreground">
              Qaror muddati:{" "}
              <span className="tabular-nums text-foreground">
                {formatExpiry(auction.second_chance_expires_at)}
              </span>
              {" · "}Eng yuqori taklif:{" "}
              <span className="font-medium tabular-nums text-foreground">
                {formatTiyin(auction.current_price)}
              </span>
            </p>
          )}
        </div>
      </div>
      <Button asChild size="sm" className="shrink-0">
        <Link href={`/lot/${auction.id}`}>
          Koʻrib chiqish
          <ArrowRightIcon aria-hidden="true" />
        </Link>
      </Button>
    </div>
  )
}

/** Sotuvchi bekor qila oladigan holatlar — sotilgan/bekor qilingan lot emas. */
const CANCELLABLE_STATUSES: ReadonlySet<ItemStatus> = new Set([
  "draft",
  "scheduled",
  "pending",
  "active",
])

/** Sotilmay tugagan auksion: taklifsiz yakunlangan yoki rezervga yetmagan. */
function isUnsold(auction: Auction | undefined): auction is Auction {
  return (
    auction != null &&
    ((auction.status === "ended" && auction.winner_id == null) ||
      auction.status === "reserve_not_met")
  )
}

function ListingCard({
  item,
  auction,
  secondChance,
  relisted,
  onCancelled,
  onRelisted,
}: {
  item: Item
  auction?: Auction
  secondChance?: Auction
  /** Bu e'londan allaqachon qayta joylangan nusxa bor. */
  relisted: boolean
  onCancelled: (item: Item) => void
  onRelisted: (auction: Auction) => void
}) {
  const [confirmOpen, setConfirmOpen] = React.useState(false)
  const [cancelling, setCancelling] = React.useState(false)
  const [cancelError, setCancelError] = React.useState<string | null>(null)
  const [relistOpen, setRelistOpen] = React.useState(false)

  const canCancel = CANCELLABLE_STATUSES.has(item.status)
  // Taklif tushgan lotni bekor qilib bo'lmaydi — xaridorlar bidi kuymasin.
  const hasBids = (auction?.bid_count ?? 0) > 0
  const unsold = isUnsold(auction)

  const doCancel = async () => {
    setCancelling(true)
    setCancelError(null)
    try {
      const updated = await cancelListing(item.id)
      onCancelled(updated)
      setConfirmOpen(false)
      toast.success("Lot bekor qilindi.")
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setCancelError("Lotga taklif tushgan yoki auksion yakunlangan — endi bekor qilib boʻlmaydi.")
      } else {
        setCancelError(e instanceof ApiError ? e.detail : "Lotni bekor qilib boʻlmadi.")
      }
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="grid gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="grid min-w-0 gap-1.5">
          <h3 className="truncate text-base font-medium text-foreground">{item.title}</h3>
          <div className="flex flex-wrap items-center gap-2">
            {unsold ? (
              <Badge variant="outline">Sotilmadi</Badge>
            ) : (
              <Badge variant={STATUS_VARIANT[item.status]}>{STATUS_LABEL[item.status]}</Badge>
            )}
            <Badge variant="outline">{CONDITION_LABEL[item.condition]}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Boshlangʻich narx:{" "}
            <span className="font-medium tabular-nums text-foreground">
              {formatTiyin(item.starting_price)}
            </span>
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {auction != null ? (
            <Button asChild variant="outline" size="sm">
              <Link href={`/lot/${auction.id}`}>Koʻrish</Link>
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground">Auksion faol emas</span>
          )}
          {unsold && !relisted && (
            <Button size="sm" onClick={() => setRelistOpen(true)}>
              <RotateCcwIcon aria-hidden="true" />
              Qayta joylash
            </Button>
          )}
          {unsold && relisted && (
            <span className="text-xs text-muted-foreground">Qayta joylangan</span>
          )}
          {canCancel && (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              disabled={hasBids}
              onClick={() => {
                setCancelError(null)
                setConfirmOpen(true)
              }}
            >
              <XIcon aria-hidden="true" />
              Bekor qilish
            </Button>
          )}
        </div>
      </div>
      {canCancel && hasBids && (
        <p className="text-xs text-muted-foreground">
          Lotga taklif tushgan — uni endi bekor qilib boʻlmaydi. Auksion muddati tugaguncha davom
          etadi.
        </p>
      )}
      {secondChance && <SecondChanceNotice auction={secondChance} />}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Lotni bekor qilasizmi?"
        description={
          <>
            <span className="font-medium text-foreground">{item.title}</span> katalogdan olib
            tashlanadi{auction != null ? " va auksion toʻxtatiladi" : ""}. Bu amalni qaytarib
            boʻlmaydi.
          </>
        }
        confirmLabel="Ha, bekor qilish"
        cancelLabel="Yoʻq"
        variant="destructive"
        loading={cancelling}
        error={cancelError}
        onConfirm={doCancel}
      />
      {unsold && !relisted && (
        <RelistDialog
          auction={auction}
          item={item}
          open={relistOpen}
          onOpenChange={setRelistOpen}
          onRelisted={(created) => {
            setRelistOpen(false)
            onRelisted(created)
          }}
        />
      )}
    </div>
  )
}

function ListingSkeletons() {
  return (
    <div className="grid gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-4">
          <div className="grid flex-1 gap-2">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-9 w-24" />
        </div>
      ))}
    </div>
  )
}

/** "Mening lotlarim"da ko'rsatiladigan auksion holatlari (bekor qilinganlar kerak emas). */
const SELLER_AUCTION_STATUSES = ["active", "scheduled", "reserve_not_met", "ended"] as const

/**
 * Sotuvchining lotlari. Tovarlar + sotuvchining O'Z auksionlari (seller_id filtri
 * bilan — ilgari butun saytning birinchi 100 ta auksioni olinib, sotuvchinikilar
 * tushib qolishi mumkin edi) birlashtiriladi. Rezervga yetmagan, ikkinchi imkoniyat
 * muddati tugamagan auksionlar uchun ogohlantirish chiqadi; sotilmay tugaganlarini
 * shu yerdan qayta joylash mumkin.
 */
function MyListings() {
  const status = useAuthStore((s) => s.status)
  const user = useAuthStore((s) => s.user)
  const pathname = usePathname()

  const [items, setItems] = React.useState<Item[] | null>(null)
  const [auctionByItem, setAuctionByItem] = React.useState<Record<number, Auction>>({})
  const [secondChanceByItem, setSecondChanceByItem] = React.useState<Record<number, Auction>>({})
  const [error, setError] = React.useState<string | null>(null)
  // Qayta joylashdan keyin ro'yxatni yangidan yuklash uchun.
  const [reloadKey, setReloadKey] = React.useState(0)

  const sellerId = user?.id

  React.useEffect(() => {
    if (status !== "authenticated" || sellerId == null) return
    let alive = true
    Promise.all([
      listSellerItems(sellerId),
      Promise.all(
        SELLER_AUCTION_STATUSES.map((s) => listSellerAuctions(sellerId, s).catch(() => []))
      ),
    ])
      .then(([its, byStatus]) => {
        if (!alive) return
        const map: Record<number, Auction> = {}
        for (const a of byStatus.flat()) map[a.item_id] = a
        const now = Date.now()
        const sc: Record<number, Auction> = {}
        for (const a of Object.values(map)) {
          if (
            a.status === "reserve_not_met" &&
            a.second_chance_expires_at &&
            new Date(a.second_chance_expires_at).getTime() > now
          ) {
            sc[a.item_id] = a
          }
        }
        setItems(its)
        setAuctionByItem(map)
        setSecondChanceByItem(sc)
      })
      .catch((e) => {
        if (!alive) return
        setError(e instanceof ApiError ? e.detail : "Mahsulotlarni yuklab boʻlmadi.")
        setItems([])
      })
    return () => {
      alive = false
    }
  }, [status, sellerId, reloadKey])

  const handleRelisted = React.useCallback(() => {
    toast.success("Lot qayta joylandi — yangi auksion boshlandi.")
    setReloadKey((k) => k + 1)
  }, [])

  // Bekor qilingan lot ro'yxatda qoladi (holati yangilanadi), auksion havolasi olinadi.
  const handleCancelled = React.useCallback((updated: Item) => {
    setItems((prev) => prev?.map((it) => (it.id === updated.id ? updated : it)) ?? prev)
    setAuctionByItem((prev) => {
      const next = { ...prev }
      delete next[updated.id]
      return next
    })
  }, [])

  if (status === "idle") {
    return <ListingSkeletons />
  }

  if (status !== "authenticated") {
    return (
      <div className="grid place-items-center gap-3 rounded-xl border border-border bg-card px-6 py-16 text-center">
        <p className="text-base font-medium text-foreground">Lotlaringizni koʻrish uchun kiring</p>
        <Button asChild size="lg">
          <Link href={`/login?next=${encodeURIComponent(pathname)}`}>Kirish</Link>
        </Button>
      </div>
    )
  }

  if (items === null) {
    return <ListingSkeletons />
  }

  if (items.length === 0) {
    return (
      <Empty className="rounded-xl border border-border bg-card">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <PackageOpenIcon aria-hidden="true" />
          </EmptyMedia>
          <EmptyTitle>Hali mahsulot joylamadingiz</EmptyTitle>
          <EmptyDescription>
            {error ?? "Birinchi tovaringizni auksionga qoʻying — bir necha daqiqada."}
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button asChild size="lg">
            <Link href="/sell">
              <PlusIcon aria-hidden="true" />
              Mahsulot joylash
            </Link>
          </Button>
        </EmptyContent>
      </Empty>
    )
  }

  const relistedSources = new Set(
    items.map((it) => it.relisted_from_id).filter((id): id is number => id != null)
  )

  return (
    <div className="grid gap-3">
      {error && (
        <p role="alert" className="text-sm font-medium text-destructive">
          {error}
        </p>
      )}
      {items.map((item) => (
        <ListingCard
          key={item.id}
          item={item}
          auction={auctionByItem[item.id]}
          secondChance={secondChanceByItem[item.id]}
          relisted={relistedSources.has(item.id)}
          onCancelled={handleCancelled}
          onRelisted={handleRelisted}
        />
      ))}
    </div>
  )
}

export { MyListings }
