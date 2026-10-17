"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { toast } from "sonner"
import { FlagIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { ApiError } from "@/lib/api/client"
import { createComplaint, type ComplaintTargetType } from "@/lib/api/complaints"
import { useAuthStore } from "@/lib/store/auth"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"

const REASONS = [
  "Soxta yoki taqiqlangan tovar",
  "Tavsif tovarga mos emas",
  "Firibgarlik shubhasi",
  "Haqoratli kontent",
  "Boshqa",
] as const

const DESCRIPTION_MAX = 2000

/** Trigger ko'rinishi — sahifada urg'u bermaydigan ikkilamchi harakat. */
const TRIGGER_CLASS =
  "text-muted-foreground hover:text-foreground"

/**
 * Qayta ishlatiladigan shikoyat oynasi (lot, foydalanuvchi va h.k.).
 * Sabab matni backend'ga tanlangan yorliqning o'zi sifatida yuboriladi —
 * moderator uni to'g'ridan-to'g'ri o'qiydi. Anonim foydalanuvchi kirishga yo'naltiriladi.
 */
function ReportDialog({
  targetType,
  targetId,
  label = "Shikoyat qilish",
  className,
}: {
  targetType: ComplaintTargetType
  targetId: number
  label?: string
  className?: string
}) {
  const status = useAuthStore((s) => s.status)
  const pathname = usePathname()

  const [open, setOpen] = React.useState(false)
  const [reason, setReason] = React.useState<string>("")
  const [description, setDescription] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [submitting, setSubmitting] = React.useState(false)

  if (status !== "authenticated") {
    return (
      <Button
        asChild
        variant="ghost"
        size="sm"
        className={cn(TRIGGER_CLASS, className)}
      >
        <Link href={`/login?next=${encodeURIComponent(pathname)}`}>
          <FlagIcon aria-hidden="true" />
          {label}
        </Link>
      </Button>
    )
  }

  const reset = () => {
    setReason("")
    setDescription("")
    setError(null)
  }

  const handleOpenChange = (next: boolean) => {
    if (submitting) return
    setOpen(next)
    if (!next) reset()
  }

  const submit = async () => {
    setError(null)
    if (!reason) {
      setError("Shikoyat sababini tanlang.")
      return
    }
    setSubmitting(true)
    try {
      const text = description.trim()
      await createComplaint({
        target_type: targetType,
        target_id: targetId,
        reason,
        ...(text ? { description: text } : {}),
      })
      toast.success("Shikoyatingiz yuborildi. Moderator koʻrib chiqadi.")
      setOpen(false)
      reset()
    } catch (e) {
      setError(
        e instanceof ApiError ? e.detail : "Shikoyat yuborilmadi. Qayta urinib koʻring."
      )
    } finally {
      setSubmitting(false)
    }
  }

  const idPrefix = `report-${targetType}-${targetId}`

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className={cn(TRIGGER_CLASS, className)}>
          <FlagIcon aria-hidden="true" />
          {label}
        </Button>
      </DialogTrigger>
      <DialogContent showCloseButton={!submitting}>
        <DialogHeader>
          <DialogTitle>Shikoyat qilish</DialogTitle>
          <DialogDescription>
            Shikoyat moderatorlarga yuboriladi. Kim yuborgani boshqa
            foydalanuvchilarga koʻrsatilmaydi.
          </DialogDescription>
        </DialogHeader>

        <fieldset className="grid gap-3" disabled={submitting}>
          <legend className="mb-2 text-sm font-medium text-foreground">Sabab</legend>
          <RadioGroup
            value={reason}
            onValueChange={(v) => {
              setReason(v)
              setError(null)
            }}
            aria-invalid={error && !reason ? true : undefined}
          >
            {REASONS.map((r, i) => (
              <div key={r} className="flex items-center gap-3">
                <RadioGroupItem value={r} id={`${idPrefix}-${i}`} />
                <Label htmlFor={`${idPrefix}-${i}`} className="font-normal leading-snug">
                  {r}
                </Label>
              </div>
            ))}
          </RadioGroup>
        </fieldset>

        <div className="grid gap-1.5">
          <Label htmlFor={`${idPrefix}-desc`}>Izoh (ixtiyoriy)</Label>
          <Textarea
            id={`${idPrefix}-desc`}
            value={description}
            maxLength={DESCRIPTION_MAX}
            disabled={submitting}
            placeholder="Nima notoʻgʻri ekanini qisqacha yozing"
            onChange={(e) => setDescription(e.target.value)}
            className="min-h-24"
          />
          <p className="text-right text-xs text-muted-foreground tabular-nums">
            {description.length} / {DESCRIPTION_MAX}
          </p>
        </div>

        {error && (
          <p role="alert" className="text-sm font-medium text-destructive">
            {error}
          </p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            disabled={submitting}
            onClick={() => handleOpenChange(false)}
          >
            Bekor qilish
          </Button>
          <Button loading={submitting} onClick={submit}>
            Yuborish
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export { ReportDialog }
