"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { InfoIcon, PlusIcon, SearchIcon, SmartphoneIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { formatTiyin } from "@/lib/format"
import { DEFECTS, DEFECT_LABEL, GRADES, GRADE_INFO, formatAdjust, formatRate } from "@/lib/device"
import { ApiError } from "@/lib/api/client"
import {
  getDeviceModel,
  getPriceGuide,
  type DeviceModel,
  type DeviceModelDetail,
  type PriceGuideInfo,
} from "@/lib/api/price-guide"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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

const dateFormatter = new Intl.DateTimeFormat("uz-UZ", {
  timeZone: "Asia/Tashkent",
  day: "numeric",
  month: "long",
  year: "numeric",
})

function seriesLabel(series: string): string {
  return /^\d+$/.test(series) ? `${series}-seriya` : series
}

/** Seriyalar bo'yicha guruhlash, yangilari tepada. */
function groupBySeries(models: DeviceModel[]): [string, DeviceModel[]][] {
  const groups = new Map<string, DeviceModel[]>()
  for (const m of models) groups.set(m.series, [...(groups.get(m.series) ?? []), m])
  return [...groups.entries()].reverse()
}

/**
 * Telefon narxlari: model tanlanadi -> xotira x daraja jadvali, daraja mezonlari,
 * nosozlik ajratmalari. Fongabi'dagi "오늘의 시세" g'oyasi: narx shaffofligi
 * sotuvchiga to'g'ri boshlang'ich narx, xaridorga esa taklif chegarasini beradi.
 */
function PriceGuideView({ initialSlug }: { initialSlug?: string }) {
  const router = useRouter()
  const [models, setModels] = React.useState<DeviceModel[] | null>(null)
  const [info, setInfo] = React.useState<PriceGuideInfo | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [slug, setSlug] = React.useState<string | undefined>(initialSlug)
  const [detail, setDetail] = React.useState<DeviceModelDetail | null>(null)
  const [query, setQuery] = React.useState("")

  React.useEffect(() => {
    let alive = true
    getPriceGuide()
      .then((r) => {
        if (!alive) return
        setModels(r.models)
        setInfo(r.info)
      })
      .catch((e) => {
        if (alive) setError(e instanceof ApiError ? e.detail : "Narxlarni yuklab boʻlmadi.")
      })
    return () => {
      alive = false
    }
  }, [])

  // URL'da model bo'lmasa yoki noto'g'ri bo'lsa — eng yangi model.
  const selected =
    models?.find((m) => m.slug === slug) ?? (models && models.length ? models[models.length - 1] : undefined)
  const selectedSlug = selected?.slug

  React.useEffect(() => {
    if (!selectedSlug) return
    let alive = true
    getDeviceModel(selectedSlug)
      .then((d) => alive && setDetail(d))
      .catch(() => alive && setDetail(null))
    return () => {
      alive = false
    }
  }, [selectedSlug])

  const choose = (next: string) => {
    setSlug(next)
    router.replace(`/narxlar?model=${next}`, { scroll: false })
  }

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    return (models ?? []).filter((m) => !q || m.name.toLowerCase().includes(q))
  }, [models, query])

  const shownDetail = detail && detail.slug === selectedSlug ? detail : null

  return (
    <div className="grid gap-6">
      <header className="grid gap-2">
        <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground uppercase md:text-3xl">
          Telefon narxlari
        </h1>
        <p className="max-w-2xl text-sm text-muted-foreground md:text-base">
          Ishlatilgan iPhone qancha turadi? Model, xotira va tashqi holat boʻyicha taxminiy
          bozor bahosi — sotishdan oldin narxni, taklif berishdan oldin chegarani biling.
        </p>
        {info && (
          <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            <InfoIcon className="size-3.5 shrink-0" aria-hidden="true" />
            Koreya bozoridagi diler narxlari asosida, 1 won = {formatRate(info.rate_tiyin_per_krw)}
            {formatAdjust(info.market_adjust_bps)
              ? `, bozor tuzatmasi ${formatAdjust(info.market_adjust_bps)}`
              : ""}
            {info.updated_at ? ` · kurs ${dateFormatter.format(new Date(info.updated_at))} yangilangan` : ""}
            . Kafolatlangan narx emas — real narx auksionda aniqlanadi.
          </p>
        )}
      </header>

      {error && (
        <p role="alert" className="text-sm font-medium text-destructive">
          {error}
        </p>
      )}

      {models === null && !error ? (
        <div className="grid gap-6 md:grid-cols-[--spacing(64)_minmax(0,1fr)]">
          <Skeleton className="hidden h-96 rounded-xl md:block" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      ) : models && models.length === 0 ? (
        <p className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">
          Narxlar hali yuklanmagan.
        </p>
      ) : models ? (
        <div className="grid gap-6 md:grid-cols-[--spacing(64)_minmax(0,1fr)] md:items-start">
          {/* Mobil: ochiladigan ro'yxat. */}
          <div className="md:hidden">
            <label htmlFor="pg-model" className="mb-1.5 block text-sm font-medium text-foreground">
              Model
            </label>
            <Select value={selectedSlug ?? ""} onValueChange={choose}>
              <SelectTrigger id="pg-model" className="w-full">
                <SelectValue placeholder="Modelni tanlang" />
              </SelectTrigger>
              <SelectContent>
                {groupBySeries(models).map(([series, list]) => (
                  <SelectGroup key={series}>
                    <SelectLabel>{seriesLabel(series)}</SelectLabel>
                    {list.map((m) => (
                      <SelectItem key={m.slug} value={m.slug}>
                        {m.name}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Desktop: qidiruvli ro'yxat. */}
          <nav
            aria-label="iPhone modellari"
            className="hidden rounded-xl border border-border bg-card p-2 md:sticky md:top-20 md:grid md:gap-2"
          >
            <div className="relative px-1 pt-1">
              <SearchIcon
                className="pointer-events-none absolute top-1/2 left-3.5 mt-0.5 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                aria-label="Modelni qidirish"
                placeholder="Masalan: 13 Pro"
                className="pl-8"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <div className="grid max-h-128 gap-3 overflow-y-auto px-1 pb-1">
              {groupBySeries(filtered).map(([series, list]) => (
                <div key={series} className="grid gap-0.5">
                  <span className="px-2 pt-1 text-xs font-medium text-muted-foreground">
                    {seriesLabel(series)}
                  </span>
                  {list.map((m) => (
                    <button
                      key={m.slug}
                      type="button"
                      aria-current={m.slug === selectedSlug ? "true" : undefined}
                      onClick={() => choose(m.slug)}
                      className={cn(
                        "rounded-md px-2 py-1.5 text-left text-sm text-foreground outline-none transition-colors duration-150 hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50",
                        m.slug === selectedSlug && "bg-primary/10 font-medium text-primary hover:bg-primary/10"
                      )}
                    >
                      {m.name}
                    </button>
                  ))}
                </div>
              ))}
              {filtered.length === 0 && (
                <p className="px-2 py-4 text-sm text-muted-foreground">Model topilmadi.</p>
              )}
            </div>
          </nav>

          {shownDetail ? <ModelPrices detail={shownDetail} /> : <Skeleton className="h-96 rounded-xl" />}
        </div>
      ) : null}
    </div>
  )
}

function ModelPrices({ detail }: { detail: DeviceModelDetail }) {
  const graded = detail.prices.some((p) => GRADES.some((g) => p[g] != null))
  const deductions = DEFECTS.filter((d) => detail.deductions[d] != null)

  return (
    <div className="grid gap-6">
      <section className="grid gap-4 rounded-xl border border-border bg-card p-4 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-lg bg-muted text-muted-foreground">
              <SmartphoneIcon className="size-5" aria-hidden="true" />
            </span>
            <div>
              <h2 className="font-heading text-xl font-semibold text-foreground md:text-2xl">{detail.name}</h2>
              <p className="text-sm text-muted-foreground">
                {detail.storages.length} xil xotira · {graded ? "holat darajasi boʻyicha" : "holatidan qatʼi nazar"}
              </p>
            </div>
          </div>
          <Button asChild size="sm">
            <Link href="/sell">
              <PlusIcon aria-hidden="true" />
              Telefonimni sotish
            </Link>
          </Button>
        </div>

        {/* Mobil: har xotira — alohida karta, darajalar ustma-ust (6 ustunli jadval 360px'ga sig'maydi). */}
        <div className="grid gap-3 sm:hidden">
          {detail.prices.map((p) => (
            <div key={p.storage} className="rounded-lg border border-border p-3">
              <p className="mb-2 text-sm font-semibold text-foreground">{p.storage}</p>
              <dl className="grid gap-1.5 text-sm">
                {graded &&
                  GRADES.map((g) => (
                    <div key={g} className="flex items-baseline justify-between gap-3">
                      <dt className="text-muted-foreground">
                        {GRADE_INFO[g].short} · {GRADE_INFO[g].label}
                      </dt>
                      <dd
                        className={cn(
                          "tabular-nums",
                          g === "a" ? "font-semibold text-foreground" : "text-foreground"
                        )}
                      >
                        {p[g] != null ? formatTiyin(p[g]) : <span className="text-muted-foreground">—</span>}
                      </dd>
                    </div>
                  ))}
                <div className="flex items-baseline justify-between gap-3">
                  <dt className="text-muted-foreground">{graded ? "Darajasiz" : "Narx"}</dt>
                  <dd className="tabular-nums text-muted-foreground">
                    {p.base != null ? formatTiyin(p.base) : "—"}
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>

        <div className="hidden overflow-x-auto sm:block">
          <table className="w-full min-w-136 border-collapse text-sm">
            <caption className="sr-only">{detail.name} taxminiy narxlari, soʻmda</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th scope="col" className="py-2 pr-3 font-medium">Xotira</th>
                {graded &&
                  GRADES.map((g) => (
                    <th key={g} scope="col" className="py-2 pr-3 text-right font-medium" title={GRADE_INFO[g].description}>
                      {GRADE_INFO[g].short}
                    </th>
                  ))}
                <th scope="col" className="py-2 text-right font-medium">
                  {graded ? "Darajasiz" : "Narx"}
                </th>
              </tr>
            </thead>
            <tbody>
              {detail.prices.map((p) => (
                <tr key={p.storage} className="border-b border-border last:border-b-0">
                  <th scope="row" className="py-2.5 pr-3 text-left font-medium text-foreground">
                    {p.storage}
                  </th>
                  {graded &&
                    GRADES.map((g) => (
                      <td
                        key={g}
                        className={cn(
                          "py-2.5 pr-3 text-right whitespace-nowrap tabular-nums",
                          g === "a" ? "font-semibold text-foreground" : "text-foreground"
                        )}
                      >
                        {p[g] != null ? formatTiyin(p[g]) : <span className="text-muted-foreground">—</span>}
                      </td>
                    ))}
                  <td className="py-2.5 text-right whitespace-nowrap tabular-nums text-muted-foreground">
                    {p.base != null ? formatTiyin(p.base) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground">
          «—» — bu holatda baholanmaydi. «Darajasiz» — holati tekshirilmagan qurilma narxi.
        </p>
      </section>

      {graded && (
        <section aria-labelledby="pg-grades" className="grid gap-3">
          <h3 id="pg-grades" className="font-heading text-lg font-semibold text-foreground">
            Holat darajalari
          </h3>
          <dl className="grid gap-3 sm:grid-cols-2">
            {GRADES.map((g) => (
              <div key={g} className="grid gap-1 rounded-xl border border-border bg-card p-4">
                <dt className="text-sm font-semibold text-foreground">
                  {GRADE_INFO[g].short} — {GRADE_INFO[g].label}
                </dt>
                <dd className="text-sm text-muted-foreground">
                  {GRADE_INFO[g].description} Batareya kamida {GRADE_INFO[g].batteryMin}%.
                </dd>
              </div>
            ))}
          </dl>
          <p className="text-xs text-muted-foreground">
            Batareya meʼyordan past boʻlsa, narx bir daraja pastroq hisoblanadi.
          </p>
        </section>
      )}

      {deductions.length > 0 && (
        <section aria-labelledby="pg-deductions" className="grid gap-3">
          <h3 id="pg-deductions" className="font-heading text-lg font-semibold text-foreground">
            Nosozlik uchun ajratmalar
          </h3>
          <ul className="grid gap-x-6 rounded-xl border border-border bg-card px-4 py-1.5 sm:grid-cols-2">
            {deductions.map((d) => (
              <li
                key={d}
                className="flex items-baseline justify-between gap-3 py-2.5 text-sm"
              >
                <span className="text-foreground">{DEFECT_LABEL[d]}</span>
                <span className="shrink-0 tabular-nums text-muted-foreground">
                  −{formatTiyin(detail.deductions[d] as string)}
                </span>
              </li>
            ))}
          </ul>
          {detail.scrap && (
            <p className="text-xs text-muted-foreground">
              Ajratmalardan keyin ham baho {formatTiyin(detail.scrap)} dan (ehtiyot qism narxi) past tushmaydi.
            </p>
          )}
        </section>
      )}
    </div>
  )
}

export { PriceGuideView }
