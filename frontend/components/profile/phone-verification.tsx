"use client"

import * as React from "react"
import { BadgeCheckIcon, RotateCwIcon, ShieldCheckIcon } from "lucide-react"
import { toast } from "sonner"

import { ApiError } from "@/lib/api/client"
import type { UserMe } from "@/lib/api/types"
import { requestPhoneOtp, updateMe, verifyPhoneOtp } from "@/lib/api/profile"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Field, FieldLabel, FieldError, FieldDescription } from "@/components/ui/field"

/** Server (OtpRequestIn) bilan bir xil cheklov: qayta so'rashdan oldin kutish. */
const RESEND_COOLDOWN_MS = 60_000
const CODE_LENGTH = 6

/**
 * Telefonni server ko'rinishiga keltiradi (bo'shliq, chiziqcha, qavslar olib
 * tashlanadi). Nega klientda ham: PATCH /users/me raqamni normallashtirmaydi,
 * OTP tasdig'i esa foydalanuvchini aynan normallashgan raqam bo'yicha qidiradi —
 * farq bo'lsa kod to'g'ri bo'lsa ham tasdiq profilga yozilmaydi.
 */
export function normalizePhone(value: string | null | undefined): string {
  return (value ?? "").trim().replace(/[\s\-()]/g, "")
}

type Props = {
  me: UserMe
  /** Formadagi joriy (hali saqlanmagan bo'lishi mumkin) telefon qiymati. */
  phone: string
  /** Profilni serverdan qayta o'qish (badge server holatini aks ettirishi uchun). */
  onRefresh: () => Promise<void>
}

/**
 * Telefon tasdiqlash bloki: raqam saqlanadi -> kod so'raladi -> kod tasdiqlanadi.
 * Badge faqat server holatidan (`phone_verified_at`) kelib chiqadi.
 */
function PhoneVerification({ me, phone, onRefresh }: Props) {
  const normalized = normalizePhone(phone)
  const saved = normalizePhone(me.phone)
  const dirty = normalized !== saved

  const [sentTo, setSentTo] = React.useState<string | null>(null)
  const [code, setCode] = React.useState("")
  const [debugCode, setDebugCode] = React.useState<string | null>(null)
  const [requesting, setRequesting] = React.useState(false)
  const [verifying, setVerifying] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [cooldownUntil, setCooldownUntil] = React.useState(0)
  const [nowMs, setNowMs] = React.useState(0)

  const remaining = Math.max(0, Math.ceil((cooldownUntil - nowMs) / 1000))

  React.useEffect(() => {
    if (cooldownUntil === 0) return
    const id = window.setInterval(() => {
      const now = Date.now()
      setNowMs(now)
      if (now >= cooldownUntil) window.clearInterval(id)
    }, 1000)
    return () => window.clearInterval(id)
  }, [cooldownUntil])

  const verified = Boolean(me.phone_verified_at) && !dirty && saved !== ""
  // Raqam o'zgarsa — eski kod boshqa raqamga tegishli, oqimni yopamiz.
  const codeStage = sentTo !== null && sentTo === normalized

  const requestCode = async () => {
    if (!normalized || requesting) return
    setError(null)
    setRequesting(true)
    try {
      // Server tasdiqni shu raqam saqlangan foydalanuvchiga yozadi — avval saqlaymiz.
      // Eski, normallashmagan ko'rinishda saqlangan raqam ham qayta yoziladi.
      if (me.phone !== normalized) {
        await updateMe({ phone: normalized })
        await onRefresh()
      }
      const res = await requestPhoneOtp(normalized)
      setSentTo(normalized)
      setCode("")
      setDebugCode(res.debug_code)
      const now = Date.now()
      setNowMs(now)
      setCooldownUntil(now + RESEND_COOLDOWN_MS)
      toast.success("Tasdiqlash kodi yuborildi.")
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Kod yuborib boʻlmadi. Qayta urinib koʻring.")
    } finally {
      setRequesting(false)
    }
  }

  const verifyCode = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sentTo || code.length !== CODE_LENGTH || verifying) return
    setError(null)
    setVerifying(true)
    try {
      const res = await verifyPhoneOtp(sentTo, code)
      if (!res.phone_verified) {
        setError("Kod toʻgʻri, lekin raqam profilingizga bogʻlanmadi. Raqamni saqlab, qayta urining.")
        return
      }
      await onRefresh()
      setSentTo(null)
      setCode("")
      setDebugCode(null)
      toast.success("Telefon raqami tasdiqlandi.")
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Kodni tekshirib boʻlmadi. Qayta urinib koʻring.")
    } finally {
      setVerifying(false)
    }
  }

  return (
    <section className="grid gap-4 rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-foreground">Telefon tasdigʻi</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Tasdiqlangan raqam xaridor va sotuvchilarga ishonch beradi.
          </p>
        </div>
        {verified ? (
          <Badge variant="success">
            <BadgeCheckIcon aria-hidden="true" />
            Tasdiqlangan
          </Badge>
        ) : (
          <Badge variant="outline">Tasdiqlanmagan</Badge>
        )}
      </div>

      {!verified && (
        <>
          {!normalized ? (
            <p className="text-sm text-muted-foreground">
              Avval yuqoridagi formada telefon raqamingizni kiriting.
            </p>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <p className="min-w-0 text-sm text-foreground tabular-nums">{normalized}</p>
              {!codeStage && (
                <Button size="sm" onClick={requestCode} loading={requesting}>
                  <ShieldCheckIcon aria-hidden="true" />
                  Tasdiqlash
                </Button>
              )}
            </div>
          )}

          {dirty && normalized && !codeStage && (
            <p className="text-xs text-muted-foreground">
              Raqam hali saqlanmagan — tasdiqlashdan oldin avtomatik saqlanadi.
            </p>
          )}

          {codeStage && (
            <form onSubmit={verifyCode} noValidate className="grid gap-3">
              <Field>
                <FieldLabel htmlFor="otp_code">SMS kod</FieldLabel>
                <Input
                  id="otp_code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]*"
                  maxLength={CODE_LENGTH}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, CODE_LENGTH))}
                  placeholder="000000"
                  aria-invalid={error ? true : undefined}
                  aria-describedby="otp_hint"
                  className="max-w-40 tracking-widest tabular-nums"
                  autoFocus
                />
                <FieldDescription id="otp_hint">
                  {sentTo} raqamiga 6 xonali kod yuborildi. Kod 5 daqiqa amal qiladi.
                </FieldDescription>
                {debugCode && (
                  <p className="text-xs text-muted-foreground">
                    Test muhiti: kod <span className="font-mono text-foreground">{debugCode}</span>
                  </p>
                )}
              </Field>

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="submit"
                  size="sm"
                  loading={verifying}
                  disabled={code.length !== CODE_LENGTH}
                >
                  Kodni tasdiqlash
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={requestCode}
                  loading={requesting}
                  disabled={remaining > 0 || verifying}
                >
                  <RotateCwIcon aria-hidden="true" />
                  {remaining > 0 ? `Qayta yuborish (${remaining} s)` : "Qayta yuborish"}
                </Button>
              </div>
            </form>
          )}

          <FieldError>{error}</FieldError>
        </>
      )}
    </section>
  )
}

export { PhoneVerification }
