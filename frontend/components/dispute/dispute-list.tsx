"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { ShieldAlertIcon, ChevronRightIcon } from "lucide-react"

import { ApiError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/store/auth"
import { listMyDisputes, type Dispute, type DisputeStatus } from "@/lib/api/engagement"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  DISPUTE_REASON_LABEL,
  DISPUTE_STATUS_LABEL,
} from "@/components/dispute/dispute-meta"
import { formatProfileDate } from "@/components/profile/profile-meta"

/** Nizo holati -> Badge varianti (token orqali rang). */
const STATUS_VARIANT: Record<DisputeStatus, "warning" | "secondary" | "success" | "neutral"> = {
  open: "warning",
  under_review: "secondary",
  resolved_buyer: "success",
  resolved_seller: "neutral",
}

function DisputeList() {
  const status = useAuthStore((s) => s.status)
  const pathname = usePathname()

  const [disputes, setDisputes] = React.useState<Dispute[] | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [loadedAuth, setLoadedAuth] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (status !== "authenticated") return
    let alive = true
    listMyDisputes()
      .then((data) => {
        if (!alive) return
        setDisputes(data)
        setError(null)
        setLoadedAuth(status)
      })
      .catch((e) => {
        if (!alive) return
        setError(e instanceof ApiError ? e.detail : "Nizolarni yuklab boʻlmadi.")
        setLoadedAuth(status)
      })
    return () => {
      alive = false
    }
  }, [status])

  if (status === "idle") {
    return <DisputeSkeleton />
  }

  if (status === "anonymous") {
    return (
      <div className="grid place-items-center gap-3 rounded-xl border border-border bg-card px-6 py-16 text-center">
        <ShieldAlertIcon className="size-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-base font-medium text-foreground">
          Nizolaringizni koʻrish uchun hisobingizga kiring.
        </p>
        <Button asChild size="sm">
          <Link href={`/login?next=${encodeURIComponent(pathname)}`}>Kirish</Link>
        </Button>
      </div>
    )
  }

  const showLoading = loadedAuth !== status

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Nizolarim</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ochgan nizolaringiz va ularning hal boʻlish holati.
        </p>
      </div>

      {showLoading ? (
        <DisputeSkeleton />
      ) : error ? (
        <div className="rounded-xl border border-border bg-card px-6 py-12 text-center">
          <p className="text-sm font-medium text-destructive">{error}</p>
        </div>
      ) : disputes && disputes.length > 0 ? (
        <ul className="grid gap-3">
          {disputes.map((dispute) => (
            <li key={dispute.id}>
              <DisputeRow dispute={dispute} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="grid place-items-center gap-2 rounded-xl border border-dashed border-border bg-card px-6 py-16 text-center">
          <ShieldAlertIcon className="size-8 text-muted-foreground" aria-hidden="true" />
          <p className="text-base font-medium text-foreground">Nizolaringiz yoʻq</p>
          <p className="text-sm text-muted-foreground">
            Buyurtmada muammo boʻlsa, buyurtma sahifasidan nizo ochishingiz mumkin.
          </p>
        </div>
      )}
    </div>
  )
}

function DisputeRow({ dispute }: { dispute: Dispute }) {
  return (
    <Link
      href={`/orders/${dispute.order_id}`}
      className="flex items-center gap-4 rounded-xl border border-border bg-card p-4 transition-colors outline-none hover:bg-muted/50 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <div className="grid size-11 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
        <ShieldAlertIcon className="size-5" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-foreground">
            Buyurtma #{dispute.order_id}
          </span>
          <Badge variant={STATUS_VARIANT[dispute.status]}>
            {DISPUTE_STATUS_LABEL[dispute.status]}
          </Badge>
        </div>
        <p className="mt-0.5 truncate text-sm text-muted-foreground">
          {DISPUTE_REASON_LABEL[dispute.reason]} · {formatProfileDate(dispute.created_at)}
        </p>
      </div>
      <ChevronRightIcon
        className="size-5 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
    </Link>
  )
}

function DisputeSkeleton() {
  return (
    <div className="grid gap-3">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-[76px] w-full rounded-xl" />
      ))}
    </div>
  )
}

export { DisputeList }
