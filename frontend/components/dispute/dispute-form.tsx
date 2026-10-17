"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import { useForm, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { ShieldAlertIcon } from "lucide-react"
import { toast } from "sonner"

import { ApiError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/store/auth"
import { createDispute, type DisputeReason } from "@/lib/api/engagement"
import { Button } from "@/components/ui/button"
import { Field, FieldLabel, FieldError, FieldDescription } from "@/components/ui/field"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Skeleton } from "@/components/ui/skeleton"
import { DISPUTE_REASONS, DISPUTE_REASON_LABEL } from "@/components/dispute/dispute-meta"

const REASON_VALUES = DISPUTE_REASONS as [DisputeReason, ...DisputeReason[]]

const schema = z.object({
  reason: z.enum(REASON_VALUES, { message: "Nizo sababini tanlang." }),
  description: z
    .string()
    .trim()
    .min(20, "Muammoni batafsilroq yozing (kamida 20 belgi).")
    .max(2000, "Matn 2000 belgidan oshmasin."),
})

type FormValues = z.infer<typeof schema>

/**
 * "Nizo ochish" formasi. Xaridor HELD hold ustidan nizo ochadi —
 * payment backend'da order bo'yicha topiladi, klientdan olinmaydi.
 */
function DisputeForm({ orderId }: { orderId: number }) {
  const status = useAuthStore((s) => s.status)
  const router = useRouter()
  const pathname = usePathname()
  const [serverError, setServerError] = React.useState<string | null>(null)

  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: { description: "" },
  })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await createDispute({
        order_id: orderId,
        reason: values.reason,
        description: values.description,
      })
      toast.success("Nizo ochildi. Admin koʻrib chiqadi.")
      router.push(`/orders/${orderId}`)
    } catch (e) {
      setServerError(
        e instanceof ApiError ? e.detail : "Nizo ochib boʻlmadi. Qayta urinib koʻring."
      )
    }
  })

  // --- Auth gate -------------------------------------------------------
  if (status === "idle") {
    return <Skeleton className="h-72 w-full rounded-xl" />
  }

  if (status === "anonymous") {
    return (
      <div className="grid place-items-center gap-3 rounded-xl border border-border bg-card px-6 py-16 text-center">
        <ShieldAlertIcon className="size-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-base font-medium text-foreground">
          Nizo ochish uchun kiring
        </p>
        <Button asChild size="sm">
          <Link href={`/login?next=${encodeURIComponent(pathname)}`}>Kirish</Link>
        </Button>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-foreground">Nizo ochish</h1>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">
        Buyurtma #{orderId} boʻyicha muammoni bildiring. Nizo davomida toʻlov
        blokda ushlab turiladi.
      </p>

      <form onSubmit={onSubmit} noValidate className="grid gap-6">
        <Field>
          <FieldLabel>Sabab</FieldLabel>
          <Controller
            control={control}
            name="reason"
            render={({ field }) => (
              <RadioGroup
                value={field.value ?? ""}
                onValueChange={field.onChange}
                aria-invalid={errors.reason ? true : undefined}
                className="gap-2"
              >
                {DISPUTE_REASONS.map((reason) => (
                  <Label
                    key={reason}
                    htmlFor={`reason-${reason}`}
                    className="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 font-normal transition-colors hover:bg-muted has-[[data-checked]]:border-primary has-[[data-checked]]:bg-muted/60"
                  >
                    <RadioGroupItem value={reason} id={`reason-${reason}`} />
                    <span className="text-sm text-foreground">
                      {DISPUTE_REASON_LABEL[reason]}
                    </span>
                  </Label>
                ))}
              </RadioGroup>
            )}
          />
          <FieldError>{errors.reason?.message}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="description">Muammo tavsifi</FieldLabel>
          <textarea
            id="description"
            rows={5}
            aria-invalid={errors.description ? true : undefined}
            placeholder="Nima yuz berdi? Qachon va qanday muammoga duch keldingiz?"
            className="w-full resize-y rounded-lg border border-input bg-transparent px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20"
            {...register("description")}
          />
          <FieldDescription>
            Batafsil yozing — bu adminga adolatli qaror qabul qilishda yordam beradi.
          </FieldDescription>
          <FieldError>{errors.description?.message}</FieldError>
        </Field>

        {serverError && (
          <p role="alert" className="text-sm font-medium text-destructive">
            {serverError}
          </p>
        )}

        <div className="flex flex-wrap gap-3">
          <Button type="submit" size="lg" loading={isSubmitting}>
            Nizo ochish
          </Button>
          <Button asChild type="button" variant="outline" size="lg">
            <Link href={`/orders/${orderId}`}>Bekor qilish</Link>
          </Button>
        </div>
      </form>
    </div>
  )
}

export { DisputeForm }
