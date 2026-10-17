"use client"

import * as React from "react"
import { CheckIcon, CopyIcon } from "lucide-react"
import { toast } from "sonner"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

/**
 * Matnni buferga nusxalaydi va 2 soniya tasdiq belgisini ko'rsatadi.
 *
 * Manba: vengeanceui `copy-button`, loyiha dizayn tizimiga moslangan:
 * hardcode ranglar (zinc/emerald) token'larga almashtirildi, `Button`
 * primitivi orqali hover/focus-visible/disabled holatlari ta'minlandi,
 * matn o'zbekchaga o'girildi va clipboard xatosi ushlanadi.
 */
function CopyButton({
  code,
  label = "Nusxalash",
  className,
}: {
  code: string
  /** Skrinrider uchun matn (ko'rinmaydi). */
  label?: string
  className?: string
}) {
  const [copied, setCopied] = React.useState(false)

  React.useEffect(() => {
    if (!copied) return
    const timeout = setTimeout(() => setCopied(false), 2000)
    return () => clearTimeout(timeout)
  }, [copied])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
    } catch {
      // HTTPS bo'lmagan kontekstda clipboard API ishlamaydi — jim qolmaymiz.
      toast.error("Nusxalab bo'lmadi. Kodni qo'lda ko'chiring.")
    }
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="icon-sm"
      onClick={copy}
      aria-label={copied ? "Nusxalandi" : label}
      className={cn("shrink-0", className)}
    >
      {copied ? (
        <CheckIcon className="text-success" aria-hidden="true" />
      ) : (
        <CopyIcon aria-hidden="true" />
      )}
    </Button>
  )
}

export { CopyButton }
