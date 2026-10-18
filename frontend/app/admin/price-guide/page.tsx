import { PriceGuideSettingsForm } from "@/components/admin/price-guide-settings"

export default function AdminPriceGuidePage() {
  return (
    <section className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Telefon narxlari</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {"Won -> so'm kursi va bozor tuzatmasi. Saqlangach saytdagi barcha baholar darhol yangilanadi."}
        </p>
      </div>
      <PriceGuideSettingsForm />
    </section>
  )
}
