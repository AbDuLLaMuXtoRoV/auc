"use client"

import * as React from "react"
import Link from "next/link"
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"

import type { Lot } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { LotCard } from "@/components/lot/lot-card"

function LotRail({
  title,
  href,
  lots,
}: {
  title: string
  href?: string
  lots: Lot[]
}) {
  const ref = React.useRef<HTMLDivElement>(null)
  const scrollBy = (dir: 1 | -1) =>
    ref.current?.scrollBy({ left: dir * 320, behavior: "smooth" })

  if (lots.length === 0) return null

  return (
    <section aria-label={title} className="mx-auto max-w-6xl px-4 pt-10 sm:px-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-xl font-semibold text-foreground">{title}</h2>
        <div className="flex items-center gap-2">
          {href && (
            <Link
              href={href}
              className="rounded-sm text-sm font-medium text-primary outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              Barchasi
            </Link>
          )}
          <div className="hidden items-center gap-1 md:flex">
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Chapga surish"
              onClick={() => scrollBy(-1)}
            >
              <ChevronLeftIcon aria-hidden="true" />
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Oʻngga surish"
              onClick={() => scrollBy(1)}
            >
              <ChevronRightIcon aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>

      <div
        ref={ref}
        className="flex snap-x gap-4 overflow-x-auto pb-2 [scrollbar-width:thin]"
      >
        {lots.map((lot) => (
          <LotCard
            key={lot.auction.id}
            lot={lot}
            className="w-40 shrink-0 snap-start sm:w-48"
          />
        ))}
      </div>
    </section>
  )
}

export { LotRail }
