"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { useForm, useWatch, Controller } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { SparklesIcon } from "lucide-react"

import { formatSom, soumToTiyin } from "@/lib/format"
import type { Category } from "@/lib/api/types"
import { listCategories } from "@/lib/api/endpoints"
import { ApiError } from "@/lib/api/client"
import { createItem, uploadItemImage, createAuction, listSellerItems } from "@/lib/api/seller"
import { useAuthStore } from "@/lib/store/auth"
import {
  DESCRIPTION_MAX,
  NO_DEFECTS_TEXT,
  autoIncrementSoum,
  buyNowError,
  categoryProfile,
  formatEndsAt,
  suggestCategorySlug,
} from "@/lib/listing"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldLabel, FieldError, FieldDescription } from "@/components/ui/field"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  RegionSelect,
  DistrictSelect,
  useRegions,
  useDistricts,
} from "@/components/region/region-select"
import { ImageDropzone, type PickedImage } from "@/components/seller/sell/image-dropzone"
import { PriceInput } from "@/components/seller/sell/price-input"
import { DevicePicker, EMPTY_DEVICE } from "@/components/seller/sell/device-picker"
import { DEFECTS, GRADES, GRADE_INFO } from "@/lib/device"
import { EquipmentChips } from "@/components/seller/sell/equipment-chips"
import { CollapsibleSection } from "@/components/seller/sell/collapsible-section"
import { ListingPreview, type PreviewData } from "@/components/seller/sell/listing-preview"
import { useSellDraft, loadSellDraft } from "@/components/seller/sell/use-sell-draft"

const CONDITIONS = [
  { value: "new", label: "Yangi" },
  { value: "used", label: "Ishlatilgan" },
  { value: "refurbished", label: "Tiklangan" },
] as const

const DURATIONS = ["3", "5", "7"] as const

const MAX_YEAR = new Date().getFullYear() + 1

function isHttpUrl(v: string): boolean {
  try {
    const u = new URL(v)
    return u.protocol === "http:" || u.protocol === "https:"
  } catch {
    return false
  }
}

const schema = z
  .object({
    title: z.string().trim().min(3, "Nom kamida 3 belgidan iborat boʻlsin.").max(160, "Nom juda uzun."),
    category_id: z.string({ error: "Kategoriyani tanlang." }).min(1, "Kategoriyani tanlang."),
    condition: z.enum(["new", "used", "refurbished"]),
    year: z
      .string()
      .trim()
      .refine(
        (v) => !v || (/^\d{4}$/.test(v) && Number(v) >= 1900 && Number(v) <= MAX_YEAR),
        `Yil 1900 va ${MAX_YEAR} oraligʻida boʻlsin.`
      ),
    description: z
      .string()
      .trim()
      .max(DESCRIPTION_MAX, `Tavsif juda uzun (koʻpi ${DESCRIPTION_MAX} belgi).`),
    no_defects: z.boolean(),
    defects: z.string().trim().max(2000, "Nuqsonlar tavsifi juda uzun (koʻpi 2000 belgi)."),
    starting_price: z.number().int().positive("Boshlangʻich narxni kiriting."),
    duration_days: z.enum(DURATIONS),
    region_id: z.string({ error: "Viloyatni tanlang." }).min(1, "Viloyatni tanlang."),
    district_id: z.string().optional(),
    equipment: z.array(z.string()),
    location: z.string().trim().max(160, "Manzil juda uzun."),
    video_url: z
      .string()
      .trim()
      .max(500, "Havola juda uzun (koʻpi 500 belgi).")
      .refine((v) => !v || isHttpUrl(v), "Toʻliq havola kiriting: https:// bilan boshlansin."),
    /** 0 — avtomatik (narxning 5%). */
    minimum_bid_increment: z.number().int().nonnegative(),
    /** 0 — zaxira narx yo'q. */
    reserve_price: z.number().int().nonnegative(),
    /** 0 — "hoziroq sotib olish" o'chiq. */
    buy_now_price: z.number().int().nonnegative(),
    /** Telefon tavsifi — faqat "telefonlar" kategoriyasida yuboriladi. */
    device: z.object({
      model_id: z.string(),
      model_name: z.string(),
      storage: z.string(),
      grade: z.enum(["", ...GRADES]),
      battery: z.number().int().min(0).max(100),
      defects: z.array(z.enum(DEFECTS)),
    }),
  })
  .superRefine((v, ctx) => {
    // Yangi tovarda nuqson bo'lmaydi; boshqa holatda — yo belgi, yo tavsif.
    if (v.condition !== "new" && !v.no_defects && v.defects.length < 3) {
      ctx.addIssue({
        code: "custom",
        path: ["defects"],
        message: "Nuqsonlarni qisqacha yozing yoki «Nuqsonlari yoʻq» belgisini qoʻying.",
      })
    }
    if (v.reserve_price > 0 && v.reserve_price < v.starting_price) {
      ctx.addIssue({
        code: "custom",
        path: ["reserve_price"],
        message: "Zaxira narx boshlangʻich narxdan past boʻlishi mumkin emas.",
      })
    }
    if (v.device.model_id && !v.device.storage) {
      ctx.addIssue({ code: "custom", path: ["device"], message: "Xotira hajmini tanlang." })
    }
    const buyNowIssue = buyNowError(v.buy_now_price, v.starting_price, v.reserve_price)
    if (buyNowIssue) {
      ctx.addIssue({ code: "custom", path: ["buy_now_price"], message: buyNowIssue })
    }
  })

type FormValues = z.infer<typeof schema>

const DEFAULTS: FormValues = {
  title: "",
  category_id: "",
  condition: "used",
  year: "",
  description: "",
  no_defects: false,
  defects: "",
  starting_price: 0,
  duration_days: "5",
  region_id: "",
  district_id: undefined,
  equipment: [],
  location: "",
  video_url: "",
  minimum_bid_increment: 0,
  reserve_price: 0,
  buy_now_price: 0,
  device: EMPTY_DEVICE,
}

type Draft = { values: FormValues; categoryTouched: boolean }

/** Qoralama faqat sotuvchi biror narsa kiritganda saqlanadi (avto-to'ldirilgan joylashuv hisob emas). */
function hasContent(v: Partial<FormValues>): boolean {
  return Boolean(
    v.title?.trim() ||
      v.description?.trim() ||
      v.defects?.trim() ||
      v.video_url?.trim() ||
      (v.starting_price ?? 0) > 0 ||
      (v.reserve_price ?? 0) > 0 ||
      (v.equipment?.length ?? 0) > 0
  )
}

function orUndef(v: string | undefined): string | undefined {
  const t = v?.trim()
  return t ? t : undefined
}

/** Radio "kartochka" — butun maydon bosiladi, tanlangani brend rangida. */
const choiceClass =
  "flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-border bg-card px-3 py-2.5 text-sm font-normal transition-colors hover:border-foreground/30 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5 has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50"

/**
 * Mahsulot joylash: tahrirlash -> ko'rib chiqish -> joylash.
 * Asosiy formada faqat zarur maydonlar; qolganlari avtomatik to'ldiriladi
 * (kategoriya — nomdan, joylashuv — oxirgi e'londan, qadam — narxdan) yoki
 * yig'iladigan bo'limlarda turadi.
 * Joylash: createItem -> rasmlar -> createAuction. Xato bo'lsa qayta urinishda
 * yaratilgan mahsulot va yuklangan rasmlar takrorlanmaydi.
 */
function SellForm() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const draft = useSellDraft<Draft>(user?.id)
  // Qoralama birinchi renderdayoq tiklanadi — effektda reset qilinsa forma bir marta bo'sh chizilardi.
  const [saved] = React.useState(() => {
    const d = loadSellDraft<Draft>(user?.id)
    return d?.values && hasContent(d.values) ? d : null
  })

  const [categories, setCategories] = React.useState<Category[] | null>(null)
  const [images, setImages] = React.useState<PickedImage[]>([])
  const [imagesError, setImagesError] = React.useState<string | null>(null)
  const [step, setStep] = React.useState<"edit" | "preview">("edit")
  const [publishing, setPublishing] = React.useState(false)
  const [publishError, setPublishError] = React.useState<string | null>(null)
  const [categoryTouched, setCategoryTouched] = React.useState(Boolean(saved?.categoryTouched))
  const [restoredDraft, setRestoredDraft] = React.useState(Boolean(saved?.values))
  const [locationSource, setLocationSource] = React.useState<"last" | null>(null)
  const [now, setNow] = React.useState<number | null>(null)

  // Qayta urinishda dublikat bo'lmasin: yaratilgan mahsulot va yuklangan rasmlar eslab qolinadi.
  const createdItemId = React.useRef<number | null>(null)
  const uploadedImageIds = React.useRef(new Set<string>())

  const {
    register,
    handleSubmit,
    control,
    setValue,
    reset,
    getValues,
    clearErrors,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onTouched",
    defaultValues: saved?.values ? { ...DEFAULTS, ...saved.values } : DEFAULTS,
  })

  const [title, categoryId, condition, noDefects, description, startingPrice, durationDays] =
    useWatch({
      control,
      name: [
        "title",
        "category_id",
        "condition",
        "no_defects",
        "description",
        "starting_price",
        "duration_days",
      ],
    })
  const regionId = useWatch({ control, name: "region_id" })
  const districtId = useWatch({ control, name: "district_id" })
  const reservePrice = useWatch({ control, name: "reserve_price" })
  const buyNowPrice = useWatch({ control, name: "buy_now_price" })
  const incrementInput = useWatch({ control, name: "minimum_bid_increment" })
  const equipmentValue = useWatch({ control, name: "equipment" })

  const category = categories?.find((c) => String(c.id) === categoryId)
  const profile = categoryProfile(category?.slug)
  // Telefon holati/baho bo'limi — narx ko'rsatkichi faqat telefonlar uchun.
  const isPhone = category?.slug === "telefonlar"
  const autoIncrement = autoIncrementSoum(startingPrice)
  const effectiveIncrement = incrementInput > 0 ? incrementInput : autoIncrement
  const endsAt = now != null ? formatEndsAt(now, Number(durationDays)) : null
  // Zaxira xatosi darhol ko'rinsin (blur kutilmasin).
  const reserveTooLow = reservePrice > 0 && startingPrice > 0 && reservePrice < startingPrice
  const buyNowIssue = buyNowError(buyNowPrice, startingPrice, reservePrice)

  const regions = useRegions()
  const districts = useDistricts(regionId ? Number(regionId) : null)

  // Tugash vaqti matni uchun joriy vaqt — render ichida Date.now ishlatilmaydi.
  React.useEffect(() => {
    const tick = () => setNow(Date.now())
    tick()
    const id = setInterval(tick, 30_000)
    return () => clearInterval(id)
  }, [])

  React.useEffect(() => {
    let alive = true
    listCategories()
      .then((c) => {
        if (alive) setCategories(c.filter((x) => x.is_active))
      })
      .catch(() => {
        if (alive) setCategories([])
      })
    return () => {
      alive = false
    }
  }, [])

  // Joylashuv qoralamada bo'lmasa — oxirgi e'londan olinadi.
  const prefillStarted = React.useRef(false)
  React.useEffect(() => {
    if (prefillStarted.current || user == null || saved?.values?.region_id) return
    prefillStarted.current = true
    listSellerItems(user.id)
      .then((items) => {
        const last = [...items]
          .filter((i) => i.region_id != null)
          .sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
        if (!last || getValues("region_id")) return
        setValue("region_id", String(last.region_id))
        if (last.district_id != null) setValue("district_id", String(last.district_id))
        if (last.location && !getValues("location")) setValue("location", last.location)
        setLocationSource("last")
      })
      .catch(() => {
        // Oxirgi e'lon topilmasa — sotuvchi o'zi tanlaydi.
      })
  }, [user, saved, setValue, getValues])

  // Har o'zgarishda qoralamani saqlash (kechiktirilgan).
  const allValues = useWatch({ control })
  React.useEffect(() => {
    // useWatch chuqur-qisman tip beradi; qoralama baribir DEFAULTS ustiga yoziladi.
    if (hasContent(allValues as Partial<FormValues>)) {
      draft.save({ values: { ...DEFAULTS, ...allValues } as FormValues, categoryTouched })
    } else {
      draft.clear()
    }
  }, [allValues, draft, categoryTouched])

  // Yil maydoni bu kategoriyada yashirin — eski (yaroqsiz) qiymat ko'rinmas xato bilan
  // yuborishni to'sib qo'ymasin.
  React.useEffect(() => {
    if (profile.showYear) return
    if (getValues("year")) setValue("year", "")
    clearErrors("year")
  }, [profile.showYear, getValues, setValue, clearErrors])

  // Kategoriya taklifi: sotuvchi o'zi tanlamaguncha nomga qarab avtomatik qo'yiladi.
  const suggestedSlug = suggestCategorySlug(title)
  const suggested = categories?.find((c) => c.slug === suggestedSlug)
  React.useEffect(() => {
    if (categoryTouched || !suggested) return
    if (getValues("category_id") !== String(suggested.id)) {
      setValue("category_id", String(suggested.id), { shouldValidate: Boolean(errors.category_id) })
    }
  }, [suggested, categoryTouched, getValues, setValue, errors.category_id])
  const categoryAuto = !categoryTouched && suggested != null && String(suggested.id) === categoryId

  // Rasmlar uchun ochilgan blob URL'lar sahifadan chiqqanda bo'shatiladi.
  const imagesRef = React.useRef(images)
  React.useEffect(() => {
    imagesRef.current = images
  }, [images])
  React.useEffect(() => () => imagesRef.current.forEach((i) => URL.revokeObjectURL(i.url)), [])

  const placeText = (() => {
    const region = regions.data?.find((r) => String(r.id) === regionId)
    const district = districts.data?.find((d) => String(d.id) === districtId)
    return [region?.name_uz, district?.name_uz, orUndef(getValues("location"))]
      .filter(Boolean)
      .join(", ")
  })()

  const toPreview = handleSubmit(
    () => {
      if (images.length === 0) {
        setImagesError("Kamida bitta rasm qoʻshing — rasmsiz mahsulotga taklif kam beriladi.")
        document.getElementById("images")?.scrollIntoView({ behavior: "smooth", block: "center" })
        return
      }
      setPublishError(null)
      setStep("preview")
      window.scrollTo({ top: 0, behavior: "smooth" })
    },
    () => {
      if (images.length === 0) setImagesError("Kamida bitta rasm qoʻshing.")
    }
  )

  const publish = async () => {
    const values = getValues()
    setPublishing(true)
    setPublishError(null)
    try {
      const startingTiyin = soumToTiyin(values.starting_price)
      const reserveTiyin = values.reserve_price > 0 ? soumToTiyin(values.reserve_price) : undefined

      if (createdItemId.current == null) {
        const item = await createItem({
          title: values.title.trim(),
          description: orUndef(values.description),
          category_id: Number(values.category_id),
          condition: values.condition,
          location: orUndef(values.location),
          year: profile.showYear && values.year ? Number(values.year) : undefined,
          equipment: values.equipment.length ? values.equipment.join(", ") : undefined,
          defects:
            values.condition === "new"
              ? undefined
              : values.no_defects
                ? NO_DEFECTS_TEXT
                : orUndef(values.defects),
          video_url: orUndef(values.video_url),
          region_id: Number(values.region_id),
          district_id: values.district_id ? Number(values.district_id) : undefined,
          starting_price: startingTiyin,
          reserve_price: reserveTiyin,
          ...(isPhone && values.device.model_id && values.device.storage
            ? {
                device_model_id: Number(values.device.model_id),
                device_storage: values.device.storage,
                device_grade: values.device.grade || undefined,
                battery_health: values.device.battery > 0 ? values.device.battery : undefined,
                device_defects: values.device.defects,
              }
            : {}),
        })
        createdItemId.current = item.id
      }
      const itemId = createdItemId.current

      // Birinchi rasm — asosiy. Yuklanganlari qayta urinishda o'tkazib yuboriladi.
      const failed: string[] = []
      for (const [index, img] of images.entries()) {
        if (uploadedImageIds.current.has(img.id)) continue
        try {
          await uploadItemImage(itemId, img.file, index === 0)
          uploadedImageIds.current.add(img.id)
        } catch (e) {
          failed.push(e instanceof ApiError ? e.detail : img.file.name)
        }
      }
      if (uploadedImageIds.current.size === 0) {
        setPublishError(
          `Rasmlar yuklanmadi${failed[0] ? `: ${failed[0]}` : ""}. Qayta urinib koʻring — mahsulot maʼlumotlari saqlangan.`
        )
        return
      }
      if (failed.length) toast.warning(`${failed.length} ta rasm yuklanmadi, qolganlari bilan joylanadi.`)

      const auction = await createAuction({
        item_id: itemId,
        start_time: new Date().toISOString(),
        duration_days: Number(values.duration_days) as 3 | 5 | 7,
        minimum_bid_increment: soumToTiyin(
          values.minimum_bid_increment > 0
            ? values.minimum_bid_increment
            : autoIncrementSoum(values.starting_price)
        ),
        reserve_price: reserveTiyin,
        buy_now_price: values.buy_now_price > 0 ? soumToTiyin(values.buy_now_price) : undefined,
      })

      draft.clear()
      toast.success("Mahsulot joylandi va auksion boshlandi")
      router.push(`/lot/${auction.id}`)
    } catch (e) {
      setPublishError(
        e instanceof ApiError ? e.detail : "Mahsulot joylashda kutilmagan xatolik. Qayta urinib koʻring."
      )
    } finally {
      setPublishing(false)
    }
  }

  const discardDraft = () => {
    draft.clear()
    reset(DEFAULTS)
    setCategoryTouched(false)
    setRestoredDraft(false)
    setLocationSource(null)
  }

  if (step === "preview") {
    const values = getValues()
    const data: PreviewData = {
      title: values.title.trim(),
      description: values.description.trim(),
      categoryName: category?.name ?? "",
      conditionLabel: CONDITIONS.find((c) => c.value === values.condition)?.label ?? "",
      year: profile.showYear ? orUndef(values.year) : undefined,
      defects:
        values.condition === "new"
          ? undefined
          : values.no_defects
            ? NO_DEFECTS_TEXT
            : orUndef(values.defects),
      equipment: values.equipment,
      startingSoum: values.starting_price,
      incrementSoum: effectiveIncrement,
      incrementIsAuto: values.minimum_bid_increment === 0,
      reserveSoum: values.reserve_price,
      buyNowSoum: values.buy_now_price,
      deviceSummary:
        isPhone && values.device.model_id && values.device.storage
          ? [
              values.device.model_name,
              values.device.storage,
              values.device.grade ? `${GRADE_INFO[values.device.grade].short} daraja` : null,
              values.device.battery > 0 ? `batareya ${values.device.battery}%` : null,
            ]
              .filter(Boolean)
              .join(" · ")
          : undefined,
      durationDays: Number(values.duration_days),
      endsAt,
      place: placeText,
      videoUrl: orUndef(values.video_url),
    }
    return (
      <ListingPreview
        data={data}
        images={images}
        publishing={publishing}
        error={publishError}
        onEdit={() => setStep("edit")}
        onPublish={publish}
      />
    )
  }

  const extrasHaveError = Boolean(errors.video_url || errors.location)
  const advancedHasError = Boolean(
    errors.reserve_price || reserveTooLow || errors.buy_now_price || buyNowIssue
  )

  return (
    <form onSubmit={toPreview} noValidate className="grid gap-6">
      {restoredDraft && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-muted/50 px-4 py-3 text-sm">
          <span className="text-muted-foreground">
            Saqlangan qoralama tiklandi. Rasmlar qoralamada saqlanmaydi — ularni qayta qoʻshing.
          </span>
          <Button type="button" variant="ghost" size="sm" onClick={discardDraft}>
            Qoralamani tozalash
          </Button>
        </div>
      )}

      <Field>
        <FieldLabel htmlFor="images">Rasmlar</FieldLabel>
        <ImageDropzone
          id="images"
          images={images}
          onChange={(next) => {
            setImages(next)
            if (next.length) setImagesError(null)
          }}
          invalid={Boolean(imagesError)}
          describedBy="images-hint"
        />
        <FieldDescription id="images-hint">
          Birinchi rasm katalogda chiqadi. Turli burchakdan va nuqsonlarni yaqindan oling.
        </FieldDescription>
        <FieldError>{imagesError}</FieldError>
      </Field>

      <Field>
        <FieldLabel htmlFor="title">Nomi</FieldLabel>
        <Input
          id="title"
          placeholder="Masalan: iPhone 13, 128 GB, koʻk"
          aria-invalid={errors.title ? true : undefined}
          {...register("title")}
        />
        <FieldError>{errors.title?.message}</FieldError>
      </Field>

      <Field>
        <FieldLabel htmlFor="category">Kategoriya</FieldLabel>
        <Controller
          control={control}
          name="category_id"
          render={({ field }) => (
            <Select
              value={field.value || ""}
              onValueChange={(v) => {
                setCategoryTouched(true)
                field.onChange(v)
              }}
              disabled={categories === null}
            >
              <SelectTrigger
                id="category"
                className="w-full"
                aria-invalid={errors.category_id ? true : undefined}
                onBlur={field.onBlur}
              >
                <SelectValue placeholder={categories === null ? "Yuklanmoqda…" : "Kategoriyani tanlang"} />
              </SelectTrigger>
              <SelectContent>
                {(categories ?? []).map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {categoryAuto && (
          <FieldDescription className="flex items-center gap-1.5">
            <SparklesIcon className="size-3.5 shrink-0 text-primary" aria-hidden="true" />
            Nomga qarab tanlandi — notoʻgʻri boʻlsa oʻzgartiring.
          </FieldDescription>
        )}
        <FieldError>{errors.category_id?.message}</FieldError>
      </Field>

      <div className={profile.showYear ? "grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]" : "grid"}>
        <Field>
          <FieldLabel id="condition-label">Holati</FieldLabel>
          <Controller
            control={control}
            name="condition"
            render={({ field }) => (
              <RadioGroup
                aria-labelledby="condition-label"
                value={field.value}
                onValueChange={field.onChange}
                className="grid-cols-3 gap-2"
              >
                {CONDITIONS.map((c) => (
                  <Label key={c.value} htmlFor={`condition-${c.value}`} className={choiceClass}>
                    <RadioGroupItem id={`condition-${c.value}`} value={c.value} />
                    {c.label}
                  </Label>
                ))}
              </RadioGroup>
            )}
          />
        </Field>

        {profile.showYear && (
          <Field>
            <FieldLabel htmlFor="year">Yili</FieldLabel>
            <Controller
              control={control}
              name="year"
              render={({ field }) => (
                <Input
                  id="year"
                  inputMode="numeric"
                  maxLength={4}
                  placeholder={String(MAX_YEAR - 3)}
                  aria-invalid={errors.year ? true : undefined}
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value.replace(/\D/g, ""))}
                  onBlur={field.onBlur}
                />
              )}
            />
            <FieldError>{errors.year?.message}</FieldError>
          </Field>
        )}
      </div>

      <Field>
        <div className="flex items-baseline justify-between gap-2">
          <FieldLabel htmlFor="description">Tavsif</FieldLabel>
          <span
            className={
              description.length > DESCRIPTION_MAX
                ? "text-xs text-destructive tabular-nums"
                : "text-xs text-muted-foreground tabular-nums"
            }
            aria-live="polite"
          >
            {description.length}/{DESCRIPTION_MAX}
          </span>
        </div>
        <Textarea
          id="description"
          rows={4}
          placeholder={profile.descriptionHint}
          aria-invalid={errors.description ? true : undefined}
          aria-describedby="description-hint"
          className="min-h-24 resize-y"
          {...register("description")}
        />
        <FieldDescription id="description-hint">Nimalarni yozish kerak: {profile.descriptionHint}</FieldDescription>
        <FieldError>{errors.description?.message}</FieldError>
      </Field>

      {isPhone && (
        <Field>
          <Controller
            control={control}
            name="device"
            render={({ field }) => (
              <DevicePicker
                value={field.value}
                onChange={field.onChange}
                title={title}
                onApplyPrice={(soum) =>
                  setValue("starting_price", soum, { shouldValidate: true, shouldDirty: true })
                }
              />
            )}
          />
          <FieldError>{errors.device?.message}</FieldError>
        </Field>
      )}

      {condition !== "new" && (
        <Field>
          <FieldLabel htmlFor={noDefects ? "no_defects" : "defects"}>Nuqsonlar</FieldLabel>
          <Controller
            control={control}
            name="no_defects"
            render={({ field }) => (
              <Label htmlFor="no_defects" className="flex w-fit cursor-pointer items-center gap-2 text-sm font-normal">
                <Checkbox
                  id="no_defects"
                  checked={field.value}
                  onCheckedChange={(v) => field.onChange(v === true)}
                />
                Nuqsonlari yoʻq
              </Label>
            )}
          />
          {!noDefects && (
            <>
              <Textarea
                id="defects"
                rows={2}
                placeholder="Masalan: orqa qopqoqda kichik tirnalish, batareya 85%"
                aria-invalid={errors.defects ? true : undefined}
                className="resize-y"
                {...register("defects")}
              />
              <FieldDescription>Halol tavsif nizolarni kamaytiradi va xaridor ishonchini oshiradi.</FieldDescription>
            </>
          )}
          <FieldError>{errors.defects?.message}</FieldError>
        </Field>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="starting_price">Boshlangʻich narx</FieldLabel>
          <Controller
            control={control}
            name="starting_price"
            render={({ field }) => (
              <PriceInput
                id="starting_price"
                placeholder="Masalan: 1 500 000"
                aria-invalid={errors.starting_price ? true : undefined}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
              />
            )}
          />
          <FieldDescription>Auksion shu narxdan boshlanadi.</FieldDescription>
          <FieldError>{errors.starting_price?.message}</FieldError>
        </Field>

        <Field>
          <FieldLabel id="duration-label">Muddat</FieldLabel>
          <Controller
            control={control}
            name="duration_days"
            render={({ field }) => (
              <RadioGroup
                aria-labelledby="duration-label"
                aria-describedby="duration-hint"
                value={field.value}
                onValueChange={field.onChange}
                className="grid-cols-3 gap-2"
              >
                {DURATIONS.map((d) => (
                  <Label key={d} htmlFor={`duration-${d}`} className={choiceClass}>
                    <RadioGroupItem id={`duration-${d}`} value={d} />
                    {d} kun
                  </Label>
                ))}
              </RadioGroup>
            )}
          />
          <FieldDescription id="duration-hint">
            {endsAt ? `${endsAt} da tugaydi (Toshkent vaqti)` : "Auksion hoziroq boshlanadi."}
          </FieldDescription>
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="region">Viloyat</FieldLabel>
          <Controller
            control={control}
            name="region_id"
            render={({ field }) => (
              <RegionSelect
                id="region"
                regions={regions}
                value={field.value || undefined}
                invalid={Boolean(errors.region_id)}
                onValueChange={(v) => {
                  field.onChange(v ?? "")
                  // Tuman faqat tanlangan viloyatga tegishli bo'lishi kerak.
                  setValue("district_id", undefined)
                  setLocationSource(null)
                }}
              />
            )}
          />
          <FieldError>{errors.region_id?.message}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="district">Tuman yoki shahar</FieldLabel>
          <Controller
            control={control}
            name="district_id"
            render={({ field }) => (
              <DistrictSelect
                id="district"
                regionId={regionId ? Number(regionId) : null}
                value={field.value}
                onValueChange={field.onChange}
              />
            )}
          />
        </Field>
      </div>
      {locationSource === "last" && (
        <p className="-mt-3 text-sm text-muted-foreground">Joylashuv oxirgi eʼloningizdan olindi.</p>
      )}

      <CollapsibleSection
        title="Qoʻshimcha maʼlumotlar"
        summary="Komplektatsiya, aniq manzil, video"
        forceOpen={extrasHaveError}
      >
        {(profile.equipment.length > 0 || equipmentValue.length > 0) && (
          <Field>
            <FieldLabel id="equipment-label">Komplektatsiya</FieldLabel>
            <Controller
              control={control}
              name="equipment"
              render={({ field }) => (
                <EquipmentChips
                  labelledBy="equipment-label"
                  options={profile.equipment}
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
            <FieldDescription>Tovar bilan birga beriladiganlarni belgilang.</FieldDescription>
          </Field>
        )}

        <Field>
          <FieldLabel htmlFor="location">Aniq manzil</FieldLabel>
          <Input
            id="location"
            placeholder="Masalan: Chilonzor 9-kvartal, Novza metrosi yonida"
            aria-invalid={errors.location ? true : undefined}
            {...register("location")}
          />
          <FieldDescription>Topshirish joyini kelishishni osonlashtiradi.</FieldDescription>
          <FieldError>{errors.location?.message}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="video_url">Video havola</FieldLabel>
          <Input
            id="video_url"
            type="url"
            inputMode="url"
            placeholder="https://youtu.be/..."
            aria-invalid={errors.video_url ? true : undefined}
            {...register("video_url")}
          />
          <FieldError>{errors.video_url?.message}</FieldError>
        </Field>
      </CollapsibleSection>

      <CollapsibleSection
        title="Kengaytirilgan sozlamalar"
        summary={
          startingPrice > 0
            ? `Minimal qadam ${formatSom(effectiveIncrement)}${incrementInput > 0 ? "" : " (avtomatik)"} · ${
                reservePrice > 0 ? `zaxira ${formatSom(reservePrice)}` : "zaxira narxsiz"
              }${buyNowPrice > 0 ? ` · hoziroq sotib olish ${formatSom(buyNowPrice)}` : ""}`
            : "Minimal qadam, zaxira narx, hoziroq sotib olish"
        }
        forceOpen={advancedHasError}
      >
        <Field>
          <FieldLabel htmlFor="minimum_bid_increment">Minimal qadam</FieldLabel>
          <Controller
            control={control}
            name="minimum_bid_increment"
            render={({ field }) => (
              <PriceInput
                id="minimum_bid_increment"
                placeholder={autoIncrement > 0 ? `Avtomatik: ${formatSom(autoIncrement)}` : "Avtomatik"}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
              />
            )}
          />
          <FieldDescription>
            Boʻsh qoldirsangiz — boshlangʻich narxning 5%. Har bir keyingi taklif kamida shuncha oshadi.
          </FieldDescription>
        </Field>

        <Field>
          <FieldLabel htmlFor="reserve_price">Zaxira narx</FieldLabel>
          <Controller
            control={control}
            name="reserve_price"
            render={({ field }) => (
              <PriceInput
                id="reserve_price"
                placeholder="Yoʻq"
                aria-invalid={reserveTooLow || errors.reserve_price ? true : undefined}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
              />
            )}
          />
          <FieldDescription>
            Shu narxga yetmasa mahsulot sotilmaydi. Xaridorlar summani koʻrmaydi, faqat zaxira borligini.
          </FieldDescription>
          <FieldError>
            {reserveTooLow
              ? "Zaxira narx boshlangʻich narxdan past boʻlishi mumkin emas."
              : errors.reserve_price?.message}
          </FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="buy_now_price">Hoziroq sotib olish narxi</FieldLabel>
          <Controller
            control={control}
            name="buy_now_price"
            render={({ field }) => (
              <PriceInput
                id="buy_now_price"
                placeholder="Yoʻq"
                aria-invalid={buyNowIssue || errors.buy_now_price ? true : undefined}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
              />
            )}
          />
          <FieldDescription>
            Xaridor kutmasdan shu narxda darhol sotib olishi mumkin. Birinchi taklif tushishi bilan
            bu imkoniyat yopiladi va oddiy auksion davom etadi.
          </FieldDescription>
          <FieldError>{buyNowIssue ?? errors.buy_now_price?.message}</FieldError>
        </Field>
      </CollapsibleSection>

      {/* Mobil: tugma ekran pastida (tabbar ustida) qotib turadi, qisqa xulosa bilan. */}
      <div className="sticky bottom-16 z-20 -mx-4 flex items-center justify-between gap-3 border-t border-border bg-background px-4 py-3 sm:-mx-6 sm:px-6 md:static md:mx-0 md:border-0 md:bg-transparent md:p-0">
        <div className="grid min-w-0 text-sm md:hidden">
          <span className="truncate font-semibold tabular-nums text-foreground">
            {startingPrice > 0 ? formatSom(startingPrice) : "Narx kiritilmagan"}
          </span>
          <span className="truncate text-xs text-muted-foreground">{durationDays} kunlik auksion</span>
        </div>
        <Button type="submit" size="lg" className="shrink-0">
          Koʻrib chiqish
        </Button>
      </div>
    </form>
  )
}

export { SellForm }
