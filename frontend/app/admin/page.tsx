import { AdminDashboard } from "@/components/admin/dashboard"

export default function AdminDashboardPage() {
  return (
    <section className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Boshqaruv paneli</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Platforma holati bir qarashda: foydalanuvchilar, auksionlar va savdo.
        </p>
      </div>
      <AdminDashboard />
    </section>
  )
}
