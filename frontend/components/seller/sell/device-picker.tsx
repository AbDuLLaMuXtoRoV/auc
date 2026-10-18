"use client"

import * as React from "react"
import Link from "next/link"
import { BatteryMediumIcon, CalculatorIcon, SparklesIcon } from "lucide-react"

import { formatNumber, formatTiyin, tiyinToSoum } from "@/lib/format"
import { DEFECTS, DEFECT_LABEL, GRADES, GRADE_INFO, formatAdjust, formatRate } from "@/lib/device"
import type { DeviceDefect, DeviceGrade } from "@/lib/api/types"
import {
  estimateDevice,
  getPriceGuide,
  type DeviceModel,
  type Estimate,
} from "@/lib/api/price-guide"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export type DeviceValue = {
  /** "" — model tanlanmagan */
  model_id: string
  /** Ko'rib chiqish sahifasi uchun (API chaqirmasdan). */
  model_name: string
  storage: string
  grade: DeviceGrade | ""
  /** 0 — kiritilmagan */
  battery: number
  defects: DeviceDefect[]
}

export const EMPTY_DEVICE: DeviceValue = {
  model_id: "",
  model_name: "",
  storage: "",
  grade: "",
  battery: 0,
  defects: [],
}

/** Taxminiy bahodan tavsiya boshlang'ich narx: 80%, 10 000 so'mga pastga. */
export function suggestStartSoum(estimateSoum: number): number {
  return Math.max(10_000, Math.floor((estimateSoum * 0.8) / 10_000) * 10_000)
}

/** Nomdan modelni topadi: eng uzun mos keladigan nom ("iPhone 13 Pro Max" > "iPhone 13"). */
function matchModel(title: string, models: DeviceModel[]): DeviceModel | undefined {
  const text = title.toLowerCase().replace(/\s+/g, " ")
  if (text.length < 6) return undefined
  return [...models]
    .sort((a, b) => b.name.length - a.name.length)
    .find((m) => {
      const name = m.name.toLowerCase()
      const i = text.indexOf(name)
      // "iphone 13" "iphone 13 pro" ichida ham uchraydi — keyingi belgi so'z davomi bo'lmasin.
      return i >= 0 && !/[a-z0-9]/.test(text.charAt(i + name.length))
    })
}

const chipClass =
  "flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-normal transition-colors hover:border-foreground/30 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5 has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50"

/**
 * Telefon modeli, xotira, daraja, batareya va nosozliklar — va shular bo'yicha
 * jonli taxminiy baho (narx ko'rsatkichi). Sotuvchi bir bosishda tavsiya
 * boshlang'ich narxni qo'llay oladi. Hozircha faqat iPhone (manba jadval).
 */
function DevicePicker({
  value,
  onChange,
  title,
  onApplyPrice,
  disabled = false,
}: {
  value: DeviceValue
  onChange: (value: DeviceValue) => void
  title: string
  onApplyPrice: (soum: number) => void
  disabled?: boolean
}) {
  const [models, setModels] = React.useState<DeviceModel[] | null>(null)
  const [loadError, setLoadError] = React.useState(false)
  const [estimate, setEstimate] = React.useState<Estimate | null>(null)
  const [estimating, setEstimating] = React.useState(false)

  React.useEffect(() => {
    let alive = true
    getPriceGuide()
      .then((r) => alive && setModels(r.models))
      .catch(() => alive && setLoadError(true))
    return () => {
      alive = false
    }
  }, [])

  const model = models?.find((m) => String(m.id) === value.model_id)
  const suggested = !value.model_id && models ? matchModel(title, models) : undefined

  // Jonli baho: tanlov o'zgarganda (qisqa kechikish bilan) qayta hisoblanadi.
  const ready = Boolean(model && value.storage)
  const key = ready
    ? JSON.stringify([value.model_id, value.storage, value.grade, value.battery, value.defects])
    : ""
  React.useEffect(() => {
    if (!key) return
    let alive = true
    const parsed = JSON.parse(key) as [string, string, DeviceGrade | "", number, DeviceDefect[]]
    const timer = window.setTimeout(() => {
      setEstimating(true)
      estimateDevice({
        model_id: Number(parsed[0]),
        storage: parsed[1],
        grade: parsed[2] || undefined,
        battery_health: parsed[3] > 0 ? parsed[3] : undefined,
        defects: parsed[4],
      })
        .then((r) => alive && setEstimate(r))
        .catch(() => alive && setEstimate(null))
        .finally(() => alive && setEstimating(false))
    }, 250)
    return () => {
      alive = false
      window.clearTimeout(timer)
    }
  }, [key])

  const set = (patch: Partial<DeviceValue>) => onChange({ ...value, ...patch })
  const pickModel = (id: string) => {
    const next = models?.find((m) => String(m.id) === id)
    // Xotira yangi modelda bo'lmasa — tozalanadi.
    set({
      model_id: id,
      model_name: next?.name ?? "",
      storage: next?.storages.includes(value.storage) ? value.storage : "",
    })
  }
  const toggleDefect = (d: DeviceDefect, on: boolean) =>
    set({ defects: on ? [...value.defects, d] : value.defects.filter((x) => x !== d) })

  const series = React.useMemo(() => {
    const groups = new Map<string, DeviceModel[]>()
    for (const m of models ?? []) groups.set(m.series, [...(groups.get(m.series) ?? []), m])
    // Yangi seriyalar tepada.
    return [...groups.entries()].reverse()
  }, [models])

  if (loadError) return null
  if (models === null) return <Skeleton className="h-40 w-full rounded-xl" />

  const shownEstimate = ready ? estimate : null
  const estimateSoum = shownEstimate ? tiyinToSoum(shownEstimate.estimate) : 0
  const batteryLow =
    value.grade !== "" && value.battery > 0 && value.battery < GRADE_INFO[value.grade].batteryMin

  return (
    <section
      aria-labelledby="device-heading"
      className="grid gap-4 rounded-xl border border-border bg-card p-4"
    >
      <div className="grid gap-1">
        <h2 id="device-heading" className="font-heading text-base font-semibold text-foreground">
          Telefon holati va narx bahosi
        </h2>
        <p className="text-sm text-muted-foreground">
          Model va holatni belgilang — kartochkada koʻrinadi va taxminiy bozor bahosini
          hisoblaymiz. Hozircha iPhone modellari.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="device-model">Model</FieldLabel>
          <Select value={value.model_id} onValueChange={pickModel} disabled={disabled}>
            <SelectTrigger id="device-model" className="w-full">
              <SelectValue placeholder="Modelni tanlang" />
            </SelectTrigger>
            <SelectContent>
              {series.map(([name, list]) => (
                <SelectGroup key={name}>
                  <SelectLabel>{/^\d+$/.test(name) ? `${name}-seriya` : name}</SelectLabel>
                  {list.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      {m.name}
                    </SelectItem>
                  ))}
                </SelectGroup>
              ))}
            </SelectContent>
          </Select>
          {suggested && (
            <Button
              type="button"
              variant="link"
              size="sm"
              className="h-auto w-fit p-0"
              disabled={disabled}
              onClick={() => pickModel(String(suggested.id))}
            >
              <SparklesIcon aria-hidden="true" />
              Nomga qarab: {suggested.name} — tanlash
            </Button>
          )}
        </Field>

        <Field>
          <FieldLabel htmlFor="device-battery">Batareya holati</FieldLabel>
          <div className="relative">
            <Input
              id="device-battery"
              inputMode="numeric"
              maxLength={3}
              placeholder="Masalan: 89"
              className="pr-10 tabular-nums"
              disabled={disabled}
              value={value.battery > 0 ? String(value.battery) : ""}
              onChange={(e) => {
                const n = Number(e.target.value.replace(/\D/g, "").slice(0, 3))
                set({ battery: Math.min(100, n) })
              }}
            />
            <span
              className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-muted-foreground"
              aria-hidden="true"
            >
              %
            </span>
          </div>
          <FieldDescription>Sozlamalar → Batareya → Batareya holati.</FieldDescription>
        </Field>
      </div>

      {model && (
        <Field>
          <FieldLabel id="device-storage-label">Xotira</FieldLabel>
          <RadioGroup
            aria-labelledby="device-storage-label"
            value={value.storage}
            onValueChange={(v) => set({ storage: v })}
            className="flex flex-wrap gap-2"
            disabled={disabled}
          >
            {model.storages.map((s) => (
              <Label key={s} htmlFor={`storage-${s}`} className={chipClass}>
                <RadioGroupItem id={`storage-${s}`} value={s} />
                {s}
              </Label>
            ))}
          </RadioGroup>
        </Field>
      )}

      <Field>
        <FieldLabel id="device-grade-label">Tashqi holat darajasi</FieldLabel>
        <RadioGroup
          aria-labelledby="device-grade-label"
          value={value.grade}
          onValueChange={(v) => set({ grade: v as DeviceGrade })}
          className="grid gap-2 sm:grid-cols-2"
          disabled={disabled}
        >
          {GRADES.map((g) => (
            <Label key={g} htmlFor={`grade-${g}`} className={`${chipClass} items-start`}>
              <RadioGroupItem id={`grade-${g}`} value={g} className="mt-0.5" />
              <span className="grid gap-0.5">
                <span className="font-medium text-foreground">
                  {GRADE_INFO[g].short} — {GRADE_INFO[g].label}
                </span>
                <span className="text-xs text-muted-foreground">{GRADE_INFO[g].description}</span>
              </span>
            </Label>
          ))}
        </RadioGroup>
        {batteryLow && value.grade !== "" && (
          <FieldDescription className="flex items-center gap-1.5">
            <BatteryMediumIcon className="size-3.5 shrink-0" aria-hidden="true" />
            Batareya {GRADE_INFO[value.grade].short} darajasi meʼyoridan (
            {GRADE_INFO[value.grade].batteryMin}%) past — baho shunga qarab pasayadi.
          </FieldDescription>
        )}
      </Field>

      <fieldset className="grid gap-2">
        <legend className="mb-2 text-sm font-medium text-foreground">Nosozliklar (boʻlsa)</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {DEFECTS.map((d) => (
            <Label
              key={d}
              htmlFor={`defect-${d}`}
              className="flex cursor-pointer items-start gap-2 text-sm font-normal text-foreground"
            >
              <Checkbox
                id={`defect-${d}`}
                checked={value.defects.includes(d)}
                disabled={disabled}
                onCheckedChange={(v) => toggleDefect(d, v === true)}
                className="mt-0.5"
              />
              {DEFECT_LABEL[d]}
            </Label>
          ))}
        </div>
      </fieldset>

      <div aria-live="polite" className="rounded-lg border border-border bg-muted/50 p-3">
        {!ready ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <CalculatorIcon className="size-4 shrink-0" aria-hidden="true" />
            Model va xotirani tanlang — taxminiy bozor bahosi shu yerda chiqadi.
          </p>
        ) : shownEstimate === null ? (
          <Skeleton className="h-16 w-full" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <div className="grid gap-1">
              <span className="text-xs text-muted-foreground">Taxminiy bozor bahosi</span>
              <span
                className={`font-heading text-xl font-semibold tabular-nums text-foreground transition-opacity duration-150 ${estimating ? "opacity-60" : ""}`}
              >
                {formatTiyin(shownEstimate.estimate)}
              </span>
              {shownEstimate.deductions.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  Holat boʻyicha {formatTiyin(shownEstimate.grade_price)}, nosozliklar uchun
                  ajratma bilan.
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                Tavsiya etilgan boshlangʻich narx:{" "}
                <span className="font-medium tabular-nums text-foreground">
                  {formatNumber(suggestStartSoum(estimateSoum))} soʻm
                </span>{" "}
                — pastroq boshlanish koʻproq ishtirokchi jalb qiladi.
              </span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={disabled}
              onClick={() => onApplyPrice(suggestStartSoum(estimateSoum))}
            >
              Narxni qoʻllash
            </Button>
            <p className="text-xs text-muted-foreground sm:col-span-2">
              Koreya diler narxlari asosida, 1 won = {formatRate(shownEstimate.info.rate_tiyin_per_krw)}
              {formatAdjust(shownEstimate.info.market_adjust_bps)
                ? `, bozor tuzatmasi ${formatAdjust(shownEstimate.info.market_adjust_bps)}`
                : ""}
              . Kafolatlangan narx emas.{" "}
              <Link
                href={model ? `/narxlar?model=${model.slug}` : "/narxlar"}
                className="rounded-sm font-medium text-primary underline-offset-4 outline-none underline decoration-foreground/30 hover:decoration-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                Barcha narxlar
              </Link>
            </p>
          </div>
        )}
      </div>
    </section>
  )
}

export { DevicePicker }
