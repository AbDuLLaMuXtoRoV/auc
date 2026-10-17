import { notFound } from "next/navigation"

import { DisputeForm } from "@/components/dispute/dispute-form"

export default async function OrderDisputePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const orderId = Number(id)
  if (!Number.isInteger(orderId) || orderId <= 0) notFound()

  return (
    <div className="mx-auto max-w-xl px-4 py-6 sm:px-6">
      <DisputeForm orderId={orderId} />
    </div>
  )
}
