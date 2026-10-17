import { DisputeList } from "@/components/dispute/dispute-list"

export const metadata = {
  title: "Nizolarim — Bazart",
}

export default function DisputesPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
      <DisputeList />
    </div>
  )
}
