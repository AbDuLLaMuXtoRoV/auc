import { WatchlistView } from "@/components/watchlist/watchlist-view"

export const metadata = {
  title: "Kuzatuvlarim — Bazart",
}

export default function WatchlistPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Kuzatuvlarim</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Kuzatayotgan lotlaringiz — tugashiga oz qolganda bildirishnoma olasiz.
        </p>
      </div>
      <WatchlistView />
    </div>
  )
}
