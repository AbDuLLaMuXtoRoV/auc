"use client"

import * as React from "react"
import Link from "next/link"
import { ImageIcon, LayersIcon, PackageIcon } from "lucide-react"

import { formatTiyin } from "@/lib/format"
import type { Lot, Category } from "@/lib/api/types"
import { listLots, listCategories } from "@/lib/api/endpoints"
import { ApiError } from "@/lib/api/client"
import { heroImage } from "@/lib/item-image"
import { Button } from "@/components/ui/button"
import { DeadlineBar } from "@/components/ui/deadline-bar"
import { ProductCardSkeleton } from "@/components/ui/skeleton"
import { LotRail } from "@/components/lot/lot-rail"
import { TrustBlock } from "@/components/site/trust-block"

function HeroLot({ lot }: { lot: Lot }) {
  const { auction, item } = lot
  const hero = heroImage(item)
  return (
    <section className="mx-auto max-w-6xl px-4 pt-6 sm:px-6">
      <div className="grid items-center gap-6 rounded-xl border border-border bg-card p-4 sm:p-6 md:grid-cols-2 md:gap-10 md:p-8">
        <div className="order-2 grid gap-4 md:order-1">
          {/* Shoshilinchni DeadlineBar (rangli countdown) bildiradi — statik
              "arafasida" badge'i mislabel bo'lgani uchun olib tashlandi. */}
          {auction.status === "active" && (
            <div className="flex items-center gap-2">
              <DeadlineBar endsAt={auction.end_time} inline />
            </div>
          )}
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-2xl">
            {item.title}
          </h1>
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="text-sm text-muted-foreground">Joriy narx</span>
            <span className="text-2xl font-semibold tabular-nums text-foreground">
              {formatTiyin(auction.current_price)}
            </span>
          </div>
          <div>
            <Button asChild size="lg">
              <Link href={`/lot/${auction.id}`}>Taklif berish</Link>
            </Button>
          </div>
        </div>
        <div className="order-1 md:order-2">
          {hero ? (
            <div className="aspect-[4/3] overflow-hidden rounded-xl border border-border bg-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={hero} alt={item.title} className="size-full object-cover" />
            </div>
          ) : (
            <div className="grid aspect-[4/3] place-items-center rounded-xl border border-border bg-muted p-6">
              <div className="flex flex-col items-center gap-3 text-center text-muted-foreground">
                <ImageIcon className="size-8" aria-hidden="true" />
                <span className="max-w-xs text-sm">{item.title}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function CategorySection({ categories }: { categories: Category[] }) {
  if (categories.length === 0) return null
  return (
    <section className="mx-auto max-w-6xl px-4 pt-10 sm:px-6">
      <h2 className="mb-4 text-xl font-semibold text-foreground">Kategoriyalar</h2>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        {categories.map((c) => (
          <li key={c.id}>
            <Link
              href={`/catalog/${c.slug}`}
              className="flex flex-col items-center gap-2 rounded-xl border border-border bg-card p-4 text-center outline-none transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <span className="grid size-10 place-items-center rounded-lg bg-muted text-foreground">
                <LayersIcon className="size-5" aria-hidden="true" />
              </span>
              <span className="text-sm font-medium text-foreground">{c.name}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

function HomeLots() {
  const [lots, setLots] = React.useState<Lot[] | null>(null)
  const [categories, setCategories] = React.useState<Category[]>([])
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let alive = true
    Promise.all([listLots(), listCategories().catch(() => [])])
      .then(([l, c]) => {
        if (alive) {
          setLots(l)
          setCategories(c)
        }
      })
      .catch((e) => {
        if (alive) {
          setError(e instanceof ApiError ? e.detail : "Ma'lumotni yuklab boʻlmadi.")
          setLots([])
        }
      })
    return () => {
      alive = false
    }
  }, [])

  if (lots === null) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  const byEnding = [...lots].sort(
    (a, b) =>
      new Date(a.auction.end_time).getTime() -
      new Date(b.auction.end_time).getTime()
  )
  const byNew = [...lots].sort(
    (a, b) =>
      new Date(b.auction.created_at).getTime() -
      new Date(a.auction.created_at).getTime()
  )

  return (
    <div className="pb-4">
      {byEnding[0] && <HeroLot lot={byEnding[0]} />}
      <CategorySection categories={categories} />
      <LotRail title="Bugun tugaydigan" href="/catalog/hammasi" lots={byEnding} />
      <LotRail title="Yangi mahsulotlar" href="/catalog/hammasi" lots={byNew} />

      {lots.length === 0 && (
        <section className="mx-auto max-w-6xl px-4 pt-10 sm:px-6">
          <div className="grid place-items-center gap-3 rounded-xl border border-border bg-card px-6 py-16 text-center">
            <PackageIcon className="size-8 text-muted-foreground" aria-hidden="true" />
            <p className="text-base font-medium text-foreground">
              Hozircha aktiv auksionlar yoʻq
            </p>
            <p className="max-w-md text-sm text-muted-foreground">
              {error
                ? error
                : "Backend ishga tushgach va mahsulotlar qoʻshilgach, ular shu yerda koʻrinadi."}
            </p>
          </div>
        </section>
      )}

      <TrustBlock />
    </div>
  )
}

export { HomeLots }
