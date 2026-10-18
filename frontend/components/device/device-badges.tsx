import { BatteryMediumIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { GRADE_INFO, gradeVariant } from "@/lib/device"
import type { Item } from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"

/**
 * Telefon e'loni belgilari: daraja, xotira, batareya. Telefon maydonlari
 * bo'lmasa hech narsa chizmaydi — oddiy e'lonlar o'zgarishsiz qoladi.
 */
function DeviceBadges({
  item,
  showGradeLabel = false,
  className,
}: {
  item: Pick<Item, "device_grade" | "device_storage" | "battery_health">
  /** "A- · Juda yaxshi" (lot sahifasi) yoki faqat "A-" (kartochka). */
  showGradeLabel?: boolean
  className?: string
}) {
  const { device_grade: grade, device_storage: storage, battery_health: battery } = item
  if (!grade && !storage && battery == null) return null

  return (
    <div className={cn("flex flex-wrap items-center gap-1", className)}>
      {grade && (
        <Badge variant={gradeVariant(grade)} title={GRADE_INFO[grade].description}>
          {GRADE_INFO[grade].short}
          {showGradeLabel && ` · ${GRADE_INFO[grade].label}`}
        </Badge>
      )}
      {storage && <Badge variant="outline">{storage}</Badge>}
      {battery != null && (
        <Badge variant="outline" className="tabular-nums">
          <BatteryMediumIcon aria-hidden="true" />
          <span className="sr-only">Batareya holati</span>
          {battery}%
        </Badge>
      )}
    </div>
  )
}

export { DeviceBadges }
