"use client"

import { CheckIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/**
 * Komplektatsiya: kategoriyaga mos tayyor variantlar, bosib tanlanadi.
 * Tanlangan qiymatlar ro'yxat sifatida saqlanadi; serverga vergul bilan birlashtirib
 * (`equipment` matn maydoni) yuboriladi — backend sxemasi o'zgarmaydi.
 */
function EquipmentChips({
  options,
  value,
  onChange,
  labelledBy,
}: {
  options: string[]
  value: string[]
  onChange: (next: string[]) => void
  labelledBy: string
}) {
  // Kategoriya almashganda avval tanlangan, yangi ro'yxatda yo'q variantlar ham ko'rinib tursin.
  const all = [...options, ...value.filter((v) => !options.includes(v))]

  return (
    <div role="group" aria-labelledby={labelledBy} className="flex flex-wrap gap-2">
      {all.map((option) => {
        const selected = value.includes(option)
        return (
          <button
            key={option}
            type="button"
            aria-pressed={selected}
            onClick={() =>
              onChange(selected ? value.filter((v) => v !== option) : [...value, option])
            }
            className={cn(
              "inline-flex h-9 items-center gap-1.5 rounded-full border px-3 text-sm outline-none transition-colors",
              "focus-visible:ring-3 focus-visible:ring-ring/50",
              selected
                ? "border-primary bg-primary/10 text-foreground hover:bg-primary/15"
                : "border-border bg-card text-muted-foreground hover:border-foreground/30 hover:text-foreground"
            )}
          >
            {selected && <CheckIcon className="size-4 text-primary" aria-hidden="true" />}
            {option}
          </button>
        )
      })}
    </div>
  )
}

export { EquipmentChips }
