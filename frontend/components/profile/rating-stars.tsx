import { StarIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/**
 * Yulduzli reyting KO'RSATKICHI (faqat o'qish uchun).
 *
 * Interaktiv baho tanlagich uchun `components/review/star-rating.tsx` bor —
 * bu esa tayyor reytingni ko'rsatadi (5 yulduz, `value` ga qadar to'ldirilgan).
 * Rang faqat token orqali: to'la yulduz `fill-warning text-warning`.
 */
function RatingStars({
  value,
  count,
  showValue = false,
  size = "sm",
  className,
}: {
  value: number
  /** Baholar soni (masalan "(12)"). */
  count?: number
  /** Raqamli qiymatni ko'rsatish (masalan "4.8"). */
  showValue?: boolean
  size?: "sm" | "md"
  className?: string
}) {
  const rounded = Math.round(value)
  const iconSize = size === "md" ? "size-5" : "size-4"

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <div
        className="flex items-center gap-0.5"
        role="img"
        aria-label={`${value.toFixed(1)} yulduz${count != null ? `, ${count} baho` : ""}`}
      >
        {Array.from({ length: 5 }).map((_, i) => (
          <StarIcon
            key={i}
            aria-hidden="true"
            className={cn(
              iconSize,
              i < rounded
                ? "fill-warning text-warning"
                : "fill-none text-muted-foreground/40"
            )}
          />
        ))}
      </div>
      {showValue && (
        <span className="font-mono text-sm font-medium tabular-nums text-foreground">
          {value.toFixed(1)}
        </span>
      )}
      {count != null && (
        <span className="text-sm text-muted-foreground">({count})</span>
      )}
    </div>
  )
}

export { RatingStars }
