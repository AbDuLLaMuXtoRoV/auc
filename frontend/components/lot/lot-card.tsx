"use client"

import Link from "next/link"
import { ImageIcon, GavelIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { formatTiyin } from "@/lib/format"
import type { Lot, ItemCondition } from "@/lib/api/types"
import { heroImage } from "@/lib/item-image"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DeadlineBar } from "@/components/ui/deadline-bar"

const CONDITION: Record<
  ItemCondition,
  { label: string; variant: "default" | "secondary" }
> = {
  new: { label: "Yangi", variant: "default" },
  used: { label: "Ishlatilgan", variant: "secondary" },
  refurbished: { label: "Tiklangan", variant: "secondary" },
}

function LotCard({ lot, className }: { lot: Lot; className?: string }) {
  const { auction, item } = lot
  const cond = CONDITION[item.condition]
  const href = `/lot/${auction.id}`
  const ended = auction.status !== "active"
  const hero = heroImage(item)

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xs transition-shadow duration-200 hover:shadow-md",
        className
      )}
    >
      <Link
        href={href}
        aria-label={item.title}
        className="relative block aspect-square overflow-hidden rounded-t-xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {hero ? (
          // Backend host'idagi rasm — next/image emas, oddiy img: host prod'da
          // o'zgaruvchan va `remotePatterns` ga bog'lanib qolmaslik uchun.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={hero}
            alt={item.title}
            loading="lazy"
            className="absolute inset-0 size-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 grid place-items-center bg-muted p-3">
            <div className="flex flex-col items-center gap-2 text-center text-muted-foreground">
              <ImageIcon className="size-6" aria-hidden="true" />
              <span className="line-clamp-3 text-xs">{item.title}</span>
            </div>
          </div>
        )}

        <div className="pointer-events-none absolute inset-x-2 top-2 flex flex-col items-start gap-1">
          <Badge variant={cond.variant}>{cond.label}</Badge>
        </div>

        {ended ? (
          <div className="absolute inset-0 grid place-items-center bg-background/60">
            <Badge variant="neutral" className="h-6 px-3 text-sm">
              Tugagan
            </Badge>
          </div>
        ) : (
          <DeadlineBar endsAt={auction.end_time} />
        )}
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <Link
          href={href}
          tabIndex={-1}
          className="outline-none focus-visible:underline"
        >
          <h3 className="line-clamp-2 min-h-10 text-sm font-medium text-foreground">
            {item.title}
          </h3>
        </Link>

        <div className="mt-auto grid gap-0.5">
          <span className="text-xs text-muted-foreground">Joriy narx</span>
          <span className="text-base font-semibold tabular-nums text-foreground">
            {formatTiyin(auction.current_price)}
          </span>
        </div>

        <Button asChild variant="secondary" size="sm" className="mt-1 w-full">
          <Link href={href}>
            <GavelIcon aria-hidden="true" />
            Taklif berish
          </Link>
        </Button>
      </div>
    </div>
  )
}

export { LotCard }
