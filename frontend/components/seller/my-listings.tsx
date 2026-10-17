"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { ArrowRightIcon, PackageOpenIcon, PlusIcon, TriangleAlertIcon } from "lucide-react"

import { formatTiyin } from "@/lib/format"
import type { Auction, Item, ItemStatus, ItemCondition } from "@/lib/api/types"
import { listAuctions } from "@/lib/api/endpoints"
import { listSellerItems } from "@/lib/api/seller"
import { ApiError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/store/auth"
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

function ListingCard({
  item,
  auctionId,
  secondChance,
}: {
  item: Item
  auctionId?: number
  secondChance?: Auction
}) {
  return (
    <div className="grid gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="grid min-w-0 gap-1.5">
          <h3 className="truncate text-base font-medium text-foreground">{item.title}</h3>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={STATUS_VARIANT[item.status]}>{STATUS_LABEL[item.status]}</Badge>
            <Badge variant="outline">{CONDITION_LABEL[item.condition]}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Boshlangʻich narx:{" "}
            <span className="font-medium tabular-nums text-foreground">
              {formatTiyin(item.starting_price)}
            </span>
          </p>
        </div>
        <div className="shrink-0">
          {auctionId != null ? (
            <Button asChild variant="outline" size="sm">
              <Link href={`/lot/${auctionId}`}>Koʻrish</Link>
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground">Auksion faol emas</span>
          )}
        </div>
      </div>
      {secondChance && <SecondChanceNotice auction={secondChance} />}
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

/**
 * Sotuvchining lotlari. Foydalanuvchi tovarlari + faol auksionlar birlashtiriladi:
 * har tovarga faol auksion topilsa "Koʻrish" havolasi /lot/{auctionId} ga oʻtadi.
 * Rezervga yetmagan, ikkinchi imkoniyat muddati tugamagan auksionlar uchun alohida
 * ogohlantirish chiqadi — sotuvchi lot sahifasida eng yuqori taklifni qabul qila oladi.
 */
function MyListings() {
  const status = useAuthStore((s) => s.status)
  const user = useAuthStore((s) => s.user)
  const pathname = usePathname()

  const [items, setItems] = React.useState<Item[] | null>(null)
  const [auctionByItem, setAuctionByItem] = React.useState<Record<number, number>>({})
  const [secondChanceByItem, setSecondChanceByItem] = React.useState<Record<number, Auction>>({})
  const [error, setError] = React.useState<string | null>(null)

  const sellerId = user?.id

  React.useEffect(() => {
    if (status !== "authenticated" || sellerId == null) return
    let alive = true
    Promise.all([
      listSellerItems(sellerId),
      listAuctions("active", 100).catch(() => []),
      listAuctions("reserve_not_met", 100).catch(() => []),
    ])
      .then(([its, aucs, unmet]) => {
        if (!alive) return
        const map: Record<number, number> = {}
        for (const a of aucs) map[a.item_id] = a.id
        const now = Date.now()
        const sc: Record<number, Auction> = {}
        for (const a of unmet) {
          if (
            a.seller_id === sellerId &&
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
  }, [status, sellerId])

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
          auctionId={auctionByItem[item.id]}
          secondChance={secondChanceByItem[item.id]}
        />
      ))}
    </div>
  )
}

export { MyListings }
