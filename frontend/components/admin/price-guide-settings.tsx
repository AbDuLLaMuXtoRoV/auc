"use client"

import * as React from "react"
import Link from "next/link"
import { ExternalLinkIcon } from "lucide-react"
import { toast } from "sonner"

import { ApiError } from "@/lib/api/client"
import {
  getPriceGuideSettings,
  updatePriceGuideSettings,
  type PriceGuideInfo,
} from "@/lib/api/price-guide"
import { formatAdjust, formatRate } from "@/lib/device"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"

const dateFormatter = new Intl.DateTimeFormat("uz-UZ", {
  timeZone: "Asia/Tashkent",
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
})

/** "8.55" -> 855 (tiyin). Noto'g'ri bo'lsa null. Vergul ham qabul qilinadi. */
function parseRate(text: string): number | null {
  const n = Number(text.replace(",", ".").trim())
  if (!Number.isFinite(n) || n <= 0 || n > 1000) return null
  return Math.round(n * 100)
}

/** "15" / "-5" / "2.5" -> bps. Noto'g'ri bo'lsa null. */
function parseAdjust(text: string): number | null {
  const t = text.replace(",", ".").trim()
  if (t === "") return 0
  const n = Number(t)
  if (!Number.isFinite(n) || n < -50 || n > 200) return null
  return Math.round(n * 100)
}

/**
 * Narx ko'rsatkichi sozlamasi: won -> so'm kursi va bozor tuzatmasi.
 * Manba narxlar (won) o'zgarmaydi — saqlangach saytdagi barcha baholar darhol
 * yangi kurs bilan qayta hisoblanadi.
 */
function PriceGuideSettingsForm() {
  const [info, setInfo] = React.useState<PriceGuideInfo | null>(null)
  const [rate, setRate] = React.useState("")
  const [adjust, setAdjust] = React.useState("")
  const [saving, setSaving] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let alive = true
    getPriceGuideSettings()
      .then((r) => {
        if (!alive) return
        setInfo(r)
        setRate((r.rate_tiyin_per_krw / 100).toFixed(2))
        setAdjust(String(r.market_adjust_bps / 100))
      })
      .catch((e) => alive && setError(e instanceof ApiError ? e.detail : "Sozlamani yuklab boʻlmadi."))
    return () => {
      alive = false
    }
  }, [])

  const rateTiyin = parseRate(rate)
  const adjustBps = parseAdjust(adjust)

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (rateTiyin == null || adjustBps == null) return
    setSaving(true)
    try {
      const updated = await updatePriceGuideSettings({
        rate_tiyin_per_krw: rateTiyin,
        market_adjust_bps: adjustBps,
      })
      setInfo(updated)
      toast.success("Kurs saqlandi — narxlar yangilandi.")
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Saqlab boʻlmadi.")
    } finally {
      setSaving(false)
    }
  }

  if (info === null && !error) return <Skeleton className="h-64 w-full max-w-xl rounded-xl" />

  return (
    <form onSubmit={save} className="grid max-w-xl gap-5 rounded-xl border border-border bg-card p-5">
      {info && (
        <p className="text-sm text-muted-foreground">
          Hozir: 1 won = <span className="font-medium text-foreground">{formatRate(info.rate_tiyin_per_krw)}</span>
          {formatAdjust(info.market_adjust_bps) && (
            <>
              , tuzatma <span className="font-medium text-foreground">{formatAdjust(info.market_adjust_bps)}</span>
            </>
          )}
          {info.updated_at ? ` · ${dateFormatter.format(new Date(info.updated_at))}` : " · standart qiymat"}
        </p>
      )}

      <Field>
        <FieldLabel htmlFor="pg-rate">1 won necha soʻm</FieldLabel>
        <Input
          id="pg-rate"
          inputMode="decimal"
          placeholder="8.55"
          className="max-w-40 tabular-nums"
          aria-invalid={rate !== "" && rateTiyin == null ? true : undefined}
          value={rate}
          disabled={saving}
          onChange={(e) => setRate(e.target.value)}
        />
        <FieldDescription>Markaziy bank yoki Wise mid-market kursi. Masalan: 8.55</FieldDescription>
        <FieldError>{rate !== "" && rateTiyin == null ? "0 dan katta son kiriting (masalan 8.55)." : null}</FieldError>
      </Field>

      <Field>
        <FieldLabel htmlFor="pg-adjust">Bozor tuzatmasi, %</FieldLabel>
        <Input
          id="pg-adjust"
          inputMode="decimal"
          placeholder="0"
          className="max-w-40 tabular-nums"
          aria-invalid={adjustBps == null ? true : undefined}
          value={adjust}
          disabled={saving}
          onChange={(e) => setAdjust(e.target.value)}
        />
        <FieldDescription>
          Manba — Koreya diler (sotib olish) narxlari. Oʻzbekistonda ishlatilgan telefonlar
          odatda qimmatroq: masalan +15 barcha baholarni 15% oshiradi. Manfiy ham boʻlishi mumkin.
        </FieldDescription>
        <FieldError>{adjustBps == null ? "−50 dan 200 gacha son kiriting." : null}</FieldError>
      </Field>

      {error && (
        <p role="alert" className="text-sm font-medium text-destructive">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" loading={saving} disabled={rateTiyin == null || adjustBps == null}>
          Saqlash
        </Button>
        <Button asChild variant="ghost" size="sm">
          <Link href="/narxlar" target="_blank">
            <ExternalLinkIcon aria-hidden="true" />
            Narxlar sahifasi
          </Link>
        </Button>
      </div>
    </form>
  )
}

export { PriceGuideSettingsForm }
