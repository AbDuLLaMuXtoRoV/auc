import type { Metadata } from "next"

import { PriceGuideView } from "@/components/price-guide/price-guide-view"

export const metadata: Metadata = {
  title: "Telefon narxlari — Bazart",
  description:
    "Ishlatilgan iPhone'ning taxminiy bozor bahosi: model, xotira va tashqi holat boʻyicha.",
}

export default async function PriceGuidePage({
  searchParams,
}: {
  searchParams: Promise<{ model?: string }>
}) {
  const { model } = await searchParams
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <PriceGuideView initialSlug={typeof model === "string" ? model : undefined} />
    </div>
  )
}
