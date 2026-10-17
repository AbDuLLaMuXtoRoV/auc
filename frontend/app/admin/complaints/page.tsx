import { AdminComplaintsTable } from "@/components/admin/complaints-table"

export default function AdminComplaintsPage() {
  return (
    <section className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Shikoyatlar</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Foydalanuvchilar yuborgan shikoyatlarni koʻrib chiqing, hal qiling yoki rad eting.
        </p>
      </div>
      <AdminComplaintsTable />
    </section>
  )
}
