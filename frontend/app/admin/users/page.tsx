import { AdminUsersTable } from "@/components/admin/users-table"

export default function AdminUsersPage() {
  return (
    <section className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Foydalanuvchilar</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Hisoblarni qidiring, bloklang yoki blokdan chiqaring. Rol berish — superadmin huquqi.
        </p>
      </div>
      <AdminUsersTable />
    </section>
  )
}
