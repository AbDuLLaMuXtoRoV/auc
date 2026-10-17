"use client"

import * as React from "react"
import { StarIcon } from "lucide-react"

import { cn } from "@/lib/utils"

const STARS = [1, 2, 3, 4, 5] as const

const RATING_LABEL: Record<number, string> = {
  1: "Juda yomon",
  2: "Yomon",
  3: "Oʻrtacha",
  4: "Yaxshi",
  5: "Aʼlo",
}

/**
 * Yulduzli baho tanlagich (1-5). Klaviatura bilan boshqariladi
 * (Tab bilan har yulduzga o'tiladi, Enter/Space tanlaydi).
 */
function StarRating({
  value,
  onChange,
  disabled = false,
  invalid = false,
}: {
  value: number
  onChange: (v: number) => void
  disabled?: boolean
  invalid?: boolean
}) {
  const [hover, setHover] = React.useState(0)
  const active = hover || value

  return (
    <div
      role="radiogroup"
      aria-label="Baho"
      aria-invalid={invalid ? true : undefined}
      className="flex items-center gap-1"
    >
      {STARS.map((star) => {
        const filled = star <= active
        return (
          <button
            key={star}
            type="button"
            role="radio"
            aria-checked={value === star}
            aria-label={`${star} yulduz — ${RATING_LABEL[star]}`}
            disabled={disabled}
            onClick={() => onChange(star)}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            onFocus={() => setHover(star)}
            onBlur={() => setHover(0)}
            className="rounded-md p-0.5 outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <StarIcon
              className={cn(
                "size-8 transition-colors",
                filled ? "fill-warning text-warning" : "text-muted-foreground"
              )}
              aria-hidden="true"
            />
          </button>
        )
      })}
      <span
        className="ml-2 min-w-20 text-sm text-muted-foreground"
        aria-hidden="true"
      >
        {active ? RATING_LABEL[active] : "Baho tanlang"}
      </span>
    </div>
  )
}

export { StarRating }
