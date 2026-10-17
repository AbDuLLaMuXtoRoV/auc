"use client"

import * as React from "react"

import { formatNumber } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"

/**
 * So'mdagi summa kiritish: "1 500 000" ko'rinishida guruhlab ko'rsatadi, ichida
 * butun son saqlaydi. 0 — "kiritilmagan" (bo'sh maydon), placeholder adashtirmasin.
 */
function PriceInput({
  value,
  onChange,
  className,
  placeholder,
  ...props
}: Omit<React.ComponentProps<"input">, "value" | "onChange" | "type"> & {
  value: number
  onChange: (value: number) => void
}) {
  return (
    <div className={cn("relative", className)}>
      <Input
        inputMode="numeric"
        autoComplete="off"
        placeholder={placeholder}
        className="pr-12 tabular-nums"
        value={value > 0 ? formatNumber(value) : ""}
        onChange={(e) => {
          const digits = e.target.value.replace(/\D/g, "").slice(0, 13)
          onChange(digits ? Number(digits) : 0)
        }}
        {...props}
      />
      <span
        className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-muted-foreground"
        aria-hidden="true"
      >
        soʻm
      </span>
    </div>
  )
}

export { PriceInput }
