"use client"

import * as React from "react"
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"

import type { Lot } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { LotCard } from "@/components/lot/lot-card"
import { SectionHeading } from "@/components/site/section-heading"

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
    <section aria-label={title} className="mx-auto max-w-6xl px-4 pt-10 sm:px-6 md:pt-14">
      <SectionHeading
        title={title}
        href={href}
        className="mb-4 md:mb-5"
        aside={
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
        }
      />

      <div
        ref={ref}
        className="-mx-4 flex snap-x scroll-px-4 gap-3 overflow-x-auto px-4 pb-2 [scrollbar-width:none] sm:mx-0 sm:gap-4 sm:px-0 sm:[scrollbar-width:thin]"
      >
        {lots.map((lot) => (
          <LotCard
            key={lot.auction.id}
            lot={lot}
            className="w-40 shrink-0 snap-start sm:w-52"
          />
        ))}
      </div>
    </section>
  )
}

export { LotRail }
