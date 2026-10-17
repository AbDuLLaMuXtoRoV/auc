import { AdminBidsTable } from "@/components/admin/bids-table"

/** URL query'dagi ID — musbat butun son bo'lmasa e'tiborsiz qoldiriladi. */
function toId(value: string | string[] | undefined): number | undefined {
  const raw = Array.isArray(value) ? value[0] : value
  const n = Number(raw)
  return raw && Number.isInteger(n) && n > 0 ? n : undefined
}

export default async function AdminBidsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const auctionId = toId(params.auction_id)
  const bidderId = toId(params.bidder_id)
  return (
    <section className="grid gap-5">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Takliflar</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Auksion yoki ishtirokchi boʻyicha takliflarni koʻring; shill yoki firibgarlik
          aniqlansa sabab koʻrsatib bekor qiling.
        </p>
      </div>
      <AdminBidsTable
        key={`${auctionId ?? ""}-${bidderId ?? ""}`}
        initialAuctionId={auctionId}
        initialBidderId={bidderId}
      />
    </section>
  )
}
