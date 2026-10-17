import { AdminItemsTable } from "@/components/admin/items-table"

export default function AdminItemsPage() {
  return (
    <section className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Tovarlar</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Yangi tovarlarni moderatsiya qiling: tasdiqlang yoki rad eting.
        </p>
      </div>
      <AdminItemsTable />
    </section>
  )
}
