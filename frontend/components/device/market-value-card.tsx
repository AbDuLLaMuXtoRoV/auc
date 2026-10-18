"use client"

import * as React from "react"
import Link from "next/link"
import { InfoIcon, TrendingDownIcon, TrendingUpIcon } from "lucide-react"

import { formatTiyin } from "@/lib/format"
import { DEFECT_LABEL, formatAdjust, formatRate } from "@/lib/device"
import type { Auction, Item } from "@/lib/api/types"
import { estimateDevice, type Estimate } from "@/lib/api/price-guide"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

/**
 * Lot sahifasida: telefonning taxminiy bozor bahosi va joriy narx bilan solishtirish.
 * Xaridorga "bu narx arzonmi?" degan savolga tayanch beradi (Fongabi'dagi "시세" kabi).
 * Telefon maydonlari bo'lmasa yoki baho hisoblanmasa — hech narsa chizmaydi.
 */
function MarketValueCard({
  item,
  auction,
  embedded = false,
}: {
  item: Item
  auction: Auction
  /** true — narx kartasi ichida (ajratgich chiziq bilan), alohida quti emas. */
  embedded?: boolean
}) {
  const [estimate, setEstimate] = React.useState<Estimate | null>(null)
  const [failed, setFailed] = React.useState(false)

  const modelId = item.device_model_id
  const storage = item.device_storage
  const grade = item.device_grade
  const battery = item.battery_health
  const defectsKey = item.device_defects.join(",")

  React.useEffect(() => {
    if (modelId == null || !storage) return
    let alive = true
    estimateDevice({
      model_id: modelId,
      storage,
      grade: grade ?? undefined,
      battery_health: battery ?? undefined,
      defects: defectsKey ? (defectsKey.split(",") as Item["device_defects"]) : [],
    })
      .then((r) => alive && setEstimate(r))
      .catch(() => alive && setFailed(true))
    return () => {
      alive = false
    }
  }, [modelId, storage, grade, battery, defectsKey])

  if (modelId == null || !storage || failed) return null
  if (estimate === null) return <Skeleton className={embedded ? "mt-2 h-16 w-full" : "h-24 w-full rounded-xl"} />

  const value = Number(estimate.estimate)
  const current = Number(auction.current_price)
  // Faqat ko'rsatish uchun foiz — pul hisobi emas.
  const diffPct = value > 0 ? Math.round(((current - value) / value) * 100) : 0
  const below = diffPct < 0

  return (
    <section
      aria-labelledby="market-value-heading"
      className={
        embedded
          ? "mt-2 grid gap-1 border-t border-border pt-3"
          : "grid gap-2 rounded-xl border border-border bg-card p-4"
      }
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id="market-value-heading" className="text-sm text-muted-foreground">
          Taxminiy bozor bahosi
        </h2>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-label="Baho qanday hisoblanadi"
              className="rounded-full text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <InfoIcon className="size-4" aria-hidden="true" />
            </button>
          </TooltipTrigger>
          <TooltipContent>
            {estimate.model_name} {estimate.storage} uchun Koreya diler narxlari asosida, 1 won ={" "}
            {formatRate(estimate.info.rate_tiyin_per_krw)}
            {formatAdjust(estimate.info.market_adjust_bps)
              ? `, tuzatma ${formatAdjust(estimate.info.market_adjust_bps)}`
              : ""}
            . Holat, batareya va nosozliklar hisobga olingan. Kafolatlangan narx emas.
          </TooltipContent>
        </Tooltip>
      </div>
      <p
        className={`font-heading font-semibold tabular-nums text-foreground ${embedded ? "text-lg" : "text-xl"}`}
      >
        {formatTiyin(estimate.estimate)}
      </p>
      {diffPct !== 0 && (
        <p
          className={`flex items-center gap-1.5 text-sm ${below ? "text-success" : "text-muted-foreground"}`}
        >
          {below ? (
            <TrendingDownIcon className="size-4 shrink-0" aria-hidden="true" />
          ) : (
            <TrendingUpIcon className="size-4 shrink-0" aria-hidden="true" />
          )}
          Joriy narx bahodan {Math.abs(diffPct)}% {below ? "past" : "yuqori"}
        </p>
      )}
      {estimate.deductions.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Hisobga olingan nosozliklar:{" "}
          {estimate.deductions.map((d) => DEFECT_LABEL[d.defect]).join("; ")}.
        </p>
      )}
      {item.device_model && (
        <Link
          href={`/narxlar?model=${item.device_model.slug}`}
          className="w-fit rounded-sm text-sm font-medium text-primary underline-offset-4 outline-none underline decoration-foreground/30 hover:decoration-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {item.device_model.name} narxlari
        </Link>
      )}
    </section>
  )
}

export { MarketValueCard }
