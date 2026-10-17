"use client"

import * as React from "react"
import { toast } from "sonner"
import {
  ShieldCheckIcon,
  KeyRoundIcon,
  CheckCircle2Icon,
  ClockIcon,
  XCircleIcon,
  LockIcon,
  type LucideIcon,
} from "lucide-react"

import { formatTiyin } from "@/lib/format"
import type { Order } from "@/lib/api/types"
import {
  createHold,
  createHandover,
  confirmHandover,
  type Payment,
  type Handover,
} from "@/lib/api/order-flow"
import { ApiError } from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import { CopyButton } from "@/components/ui/copy-button"
import { Input } from "@/components/ui/input"
import { Field, FieldLabel, FieldError, FieldDescription } from "@/components/ui/field"
import { handoverStatusLabel } from "@/components/order/order-status"

export type OrderRole = "buyer" | "seller" | "other"

/**
 * Rolga bogʻliq escrow harakatlari paneli.
 *
 * Oqim (har tugma real endpointga ulanган):
 *   pending_payment + buyer  -> "Toʻlash (escrow hold)"  -> POST /payments/holds
 *   pickup_pending  + seller -> "Topshirish kodini yaratish" -> POST /handovers
 *   pickup_pending  + buyer  -> kod + "Tasdiqlash" -> POST /handovers/{id}/confirm
 *                               (server capture'ni ishga tushiradi -> completed)
 */
function EscrowPanel({
  order,
  payment,
  handover,
  role,
  onChanged,
}: {
  order: Order
  payment: Payment | null
  handover: Handover | null
  role: OrderRole
  onChanged: () => void
}) {
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [code, setCode] = React.useState("")

  const fail = (e: unknown, fallback: string) => {
    setError(e instanceof ApiError ? e.detail : fallback)
  }

  // --- Buyer: escrow hold ---------------------------------------------------
  const pay = async () => {
    setError(null)
    setBusy(true)
    try {
      // idempotency_key event handler ichida yaratiladi (render'da EMAS).
      const key = crypto.randomUUID()
      await createHold({
        order_id: order.id,
        idempotency_key: key,
        provider: "mock",
        currency: "UZS",
      })
      toast.success("Toʻlov bloklandi (escrow)")
      onChanged()
    } catch (e) {
      fail(e, "Toʻlovni bloklab boʻlmadi. Qayta urinib koʻring.")
    } finally {
      setBusy(false)
    }
  }

  // --- Seller: handover yaratish (kod) -------------------------------------
  const makeHandover = async () => {
    setError(null)
    setBusy(true)
    try {
      await createHandover({ order_id: order.id })
      toast.success("Topshirish kodi yaratildi")
      onChanged()
    } catch (e) {
      fail(e, "Topshirish kodini yaratib boʻlmadi.")
    } finally {
      setBusy(false)
    }
  }

  // --- Buyer: kodni tasdiqlash (capture) -----------------------------------
  const confirm = async () => {
    setError(null)
    if (code.trim().length === 0) {
      setError("Kodni kiriting.")
      return
    }
    setBusy(true)
    try {
      await confirmHandover(order.id, code.trim())
      toast.success("Tasdiqlandi — toʻlov sotuvchiga oʻtkazildi")
      onChanged()
    } catch (e) {
      fail(e, "Kodni tasdiqlab boʻlmadi.")
    } finally {
      setBusy(false)
    }
  }

  // --- Yakuniy holatlar -----------------------------------------------------
  if (order.status === "completed") {
    return (
      <PanelShell tone="success" icon={CheckCircle2Icon} title="Buyurtma yakunlandi">
        <p>
          Topshirish tasdiqlandi va bloklangan mablagʻ sotuvchiga oʻtkazildi
          (escrow release). Rahmat!
        </p>
      </PanelShell>
    )
  }

  if (order.status === "cancelled") {
    return (
      <PanelShell tone="muted" icon={XCircleIcon} title="Buyurtma bekor qilindi">
        <p>Escrow bloki bekor qilindi — mablagʻ xaridorda qoldi.</p>
      </PanelShell>
    )
  }

  // --- 1-qadam: toʻlov (escrow hold) ---------------------------------------
  if (order.status === "pending_payment") {
    if (role === "buyer") {
      return (
        <PanelShell tone="brand" icon={ShieldCheckIcon} title="1-qadam — Toʻlov (escrow hold)">
          <p>
            Toʻlov kartangizda <b>bloklanadi</b>, sotuvchiga darhol oʻtmaydi.
            Mablagʻ faqat tovarni qoʻlingizga olib, kodni tasdiqlaganingizdan
            keyin sotuvchiga oʻtkaziladi.
          </p>
          <ul className="grid gap-1 text-sm text-muted-foreground">
            <li className="flex justify-between gap-4">
              <span>Mahsulot narxi</span>
              <span className="tabular-nums text-foreground">
                {formatTiyin(order.final_price)}
              </span>
            </li>
            <li className="flex justify-between gap-4">
              <span>Xaridor mukofoti (8%)</span>
              <span className="tabular-nums text-foreground">
                {payment ? formatTiyin(payment.premium) : "hisoblanadi"}
              </span>
            </li>
          </ul>
          {error && <p role="alert" className="text-sm font-medium text-destructive">{error}</p>}
          <Button size="lg" loading={busy} onClick={pay}>
            <LockIcon aria-hidden="true" />
            Toʻlash (escrow hold)
          </Button>
        </PanelShell>
      )
    }
    return (
      <PanelShell tone="muted" icon={ClockIcon} title="Toʻlov kutilmoqda">
        <p>Xaridor escrow toʻlovni (hold) amalga oshirishini kutmoqda.</p>
      </PanelShell>
    )
  }

  // --- 2-qadam: topshirish (pickup_pending, pul held) ----------------------
  if (order.status === "pickup_pending") {
    // Sotuvchi
    if (role === "seller") {
      if (handover && handover.status === "pending") {
        return (
          <PanelShell tone="brand" icon={KeyRoundIcon} title="2-qadam — Topshirish kodi">
            <p>
              Toʻlov bloklangan. Uchrashuvda tovarni bering va quyidagi kodni
              <b> faqat xaridorga</b> ayting. Xaridor kodni kiritganda mablagʻ
              sizga oʻtkaziladi.
            </p>
            <div className="grid place-items-center gap-1 rounded-xl border border-border bg-background py-5">
              <span className="text-xs text-muted-foreground">Topshirish kodi</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-3xl font-semibold tracking-[0.3em] tabular-nums text-foreground">
                  {handover.code ?? "——————"}
                </span>
                {handover.code && (
                  <CopyButton
                    code={handover.code}
                    label="Topshirish kodini nusxalash"
                  />
                )}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Kodni oldindan yubormang — u egalik dalili. Faqat tovarni
              topshirayotganda ayting.
            </p>
          </PanelShell>
        )
      }
      return (
        <PanelShell tone="brand" icon={KeyRoundIcon} title="2-qadam — Topshirishni boshlash">
          <p>
            Xaridor toʻlovni bloklab qoʻydi (escrow). Uchrashuvni kelishing va
            topshirish kodini yarating — kodni faqat siz koʻrasiz.
          </p>
          {error && <p role="alert" className="text-sm font-medium text-destructive">{error}</p>}
          <Button size="lg" loading={busy} onClick={makeHandover}>
            <KeyRoundIcon aria-hidden="true" />
            Topshirish kodini yaratish
          </Button>
        </PanelShell>
      )
    }

    // Xaridor
    if (role === "buyer") {
      if (handover && handover.status === "pending") {
        return (
          <PanelShell tone="brand" icon={ShieldCheckIcon} title="3-qadam — Kodni tasdiqlash">
            <p>
              Tovarni qoʻlingizga olgach, sotuvchi aytgan kodni kiriting.
              Tasdiqlash bloklangan mablagʻni sotuvchiga oʻtkazadi (capture) —
              shundan keyin qaytarib boʻlmaydi.
            </p>
            <Field>
              <FieldLabel htmlFor="handover-code">Topshirish kodi</FieldLabel>
              <Input
                id="handover-code"
                inputMode="numeric"
                autoComplete="off"
                placeholder="6 xonali kod"
                value={code}
                maxLength={16}
                onChange={(e) => setCode(e.target.value)}
                aria-invalid={error ? true : undefined}
                aria-describedby="handover-code-desc"
              />
              <FieldDescription id="handover-code-desc">
                Kodni faqat tovarni tekshirib boʻlgach kiriting.
              </FieldDescription>
              <FieldError>{error}</FieldError>
            </Field>
            <Button size="lg" loading={busy} onClick={confirm}>
              <CheckCircle2Icon aria-hidden="true" />
              Tasdiqlash
            </Button>
          </PanelShell>
        )
      }
      return (
        <PanelShell tone="muted" icon={ClockIcon} title="Topshirish kutilmoqda">
          <p>
            Toʻlovingiz bloklandi (escrow). Sotuvchi topshirish kodini
            yaratishini kuting — soʻng uchrashuvda kodni kiritasiz.
          </p>
        </PanelShell>
      )
    }
  }

  // --- Fallback (paid yoki noma'lum oraliq holat) --------------------------
  return (
    <PanelShell tone="muted" icon={ClockIcon} title="Holat">
      <p>
        Buyurtma holati: {handover ? handoverStatusLabel(handover.status) : "kutilmoqda"}.
      </p>
    </PanelShell>
  )
}

type Tone = "brand" | "success" | "muted"

const TONE_CLASS: Record<Tone, string> = {
  brand: "border-primary/30 bg-primary/5",
  success: "border-success/30 bg-success/5",
  muted: "border-border bg-muted/40",
}

const ICON_CLASS: Record<Tone, string> = {
  brand: "text-primary",
  success: "text-success",
  muted: "text-muted-foreground",
}

function PanelShell({
  tone,
  icon: Icon,
  title,
  children,
}: {
  tone: Tone
  icon: LucideIcon
  title: string
  children: React.ReactNode
}) {
  return (
    <section className={"grid gap-3 rounded-xl border p-4 sm:p-5 " + TONE_CLASS[tone]}>
      <div className="flex items-center gap-2">
        <Icon className={"size-5 shrink-0 " + ICON_CLASS[tone]} aria-hidden={true} />
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
      </div>
      <div className="grid gap-3 text-sm leading-relaxed text-muted-foreground">
        {children}
      </div>
    </section>
  )
}

export { EscrowPanel }
