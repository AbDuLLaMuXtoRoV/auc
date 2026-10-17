"use client"

import * as React from "react"

import { listRegions, listDistricts, type Region, type District } from "@/lib/api/regions"
import { Spinner } from "@/components/ui/spinner"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

/** "Hammasi" varianti uchun maxsus qiymat — Radix Select boʻsh satrni element qiymati sifatida qabul qilmaydi. */
const ALL = "all"

// Hududlar deyarli oʻzgarmaydi — sahifalar orasida qayta soʻramaslik uchun modul darajasida keshlaymiz.
let regionsCache: Promise<Region[]> | null = null
const districtsCache = new Map<number, Promise<District[]>>()

function fetchRegions(): Promise<Region[]> {
  if (!regionsCache) {
    regionsCache = listRegions().catch((e) => {
      regionsCache = null
      throw e
    })
  }
  return regionsCache
}

function fetchDistricts(regionId: number): Promise<District[]> {
  let p = districtsCache.get(regionId)
  if (!p) {
    p = listDistricts(regionId).catch((e) => {
      districtsCache.delete(regionId)
      throw e
    })
    districtsCache.set(regionId, p)
  }
  return p
}

type LoadState<T> = { data: T[] | null; error: boolean }

/** Viloyatlar roʻyxati. data === null — yuklanmoqda. */
function useRegions(): LoadState<Region> {
  const [state, setState] = React.useState<LoadState<Region>>({ data: null, error: false })
  React.useEffect(() => {
    let alive = true
    fetchRegions()
      .then((data) => {
        if (alive) setState({ data, error: false })
      })
      .catch(() => {
        if (alive) setState({ data: [], error: true })
      })
    return () => {
      alive = false
    }
  }, [])
  return state
}

/** Tanlangan viloyat tumanlari. Viloyat tanlanmagan boʻlsa — boʻsh roʻyxat. */
function useDistricts(regionId: number | null): LoadState<District> & { loading: boolean } {
  const [state, setState] = React.useState<{ key: number | null } & LoadState<District>>({
    key: null,
    data: [],
    error: false,
  })
  React.useEffect(() => {
    if (regionId == null) return
    let alive = true
    fetchDistricts(regionId)
      .then((data) => {
        if (alive) setState({ key: regionId, data, error: false })
      })
      .catch(() => {
        if (alive) setState({ key: regionId, data: [], error: true })
      })
    return () => {
      alive = false
    }
  }, [regionId])

  if (regionId == null) return { data: [], error: false, loading: false }
  if (state.key !== regionId) return { data: null, error: false, loading: true }
  return { data: state.data, error: state.error, loading: false }
}

type BaseProps = {
  id?: string
  /** Tanlangan id (satr koʻrinishida) yoki undefined. */
  value: string | undefined
  onValueChange: (value: string | undefined) => void
  /** Berilsa — roʻyxat boshida "hammasi" varianti chiqadi (filtr uchun). */
  allLabel?: string
  placeholder?: string
  invalid?: boolean
  disabled?: boolean
  className?: string
  "aria-label"?: string
}

function LoadingValue() {
  return (
    <span className="flex items-center gap-2 text-muted-foreground">
      <Spinner className="size-3.5" />
      Yuklanmoqda…
    </span>
  )
}

function OptionsSelect({
  id,
  value,
  onValueChange,
  allLabel,
  placeholder,
  invalid,
  disabled,
  className,
  loading,
  options,
  emptyLabel,
  "aria-label": ariaLabel,
}: BaseProps & {
  loading: boolean
  options: { id: number; name_uz: string }[]
  emptyLabel: string
}) {
  const isEmpty = !loading && options.length === 0
  // Yuklanayotganda yoki roʻyxat boʻsh boʻlsa — placeholder (holat matni) koʻrinsin.
  const current = loading || isEmpty ? "" : (value ?? (allLabel ? ALL : ""))
  return (
    <Select
      value={current}
      onValueChange={(v) => onValueChange(v === ALL ? undefined : v)}
      disabled={disabled || loading || isEmpty}
    >
      <SelectTrigger
        id={id}
        className={className ?? "w-full"}
        aria-label={ariaLabel}
        aria-invalid={invalid ? true : undefined}
        aria-busy={loading ? true : undefined}
      >
        <SelectValue placeholder={loading ? <LoadingValue /> : isEmpty ? emptyLabel : placeholder} />
      </SelectTrigger>
      <SelectContent>
        {allLabel && <SelectItem value={ALL}>{allLabel}</SelectItem>}
        {options.map((o) => (
          <SelectItem key={o.id} value={String(o.id)}>
            {o.name_uz}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

/** Viloyat tanlash. Roʻyxat oʻzi yuklanadi. */
function RegionSelect(props: BaseProps & { regions?: LoadState<Region> }) {
  const own = useRegions()
  const { data, error } = props.regions ?? own
  return (
    <OptionsSelect
      placeholder="Viloyatni tanlang"
      {...props}
      loading={data === null}
      options={data ?? []}
      emptyLabel={error ? "Viloyatlar yuklanmadi" : "Viloyatlar roʻyxati boʻsh"}
    />
  )
}

/** Tuman tanlash — viloyat tanlanmaguncha oʻchiq; viloyat almashsa roʻyxat qayta yuklanadi. */
function DistrictSelect({ regionId, ...props }: BaseProps & { regionId: number | null }) {
  const { data, error, loading } = useDistricts(regionId)
  return (
    <OptionsSelect
      placeholder="Tumanni tanlang"
      {...props}
      disabled={props.disabled || regionId == null}
      loading={loading}
      options={data ?? []}
      emptyLabel={
        regionId == null
          ? "Avval viloyatni tanlang"
          : error
            ? "Tumanlar yuklanmadi"
            : "Bu viloyat uchun tuman yoʻq"
      }
    />
  )
}

export { RegionSelect, DistrictSelect, useRegions, useDistricts }
