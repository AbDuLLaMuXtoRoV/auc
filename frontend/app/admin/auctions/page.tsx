import { AdminAuctionsTable } from "@/components/admin/auctions-table"

export default function AdminAuctionsPage() {
  return (
    <section className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Auksionlar</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {"Faol va yakunlangan auksionlarni kuzating; kerak bo'lsa bekor qiling."}
        </p>
      </div>
      <AdminAuctionsTable />
    </section>
  )
}
