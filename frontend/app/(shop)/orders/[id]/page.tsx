import { notFound } from "next/navigation"

import { OrderDetail } from "@/components/order/order-detail"

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const orderId = Number(id)
  if (!Number.isInteger(orderId) || orderId <= 0) notFound()

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <OrderDetail orderId={orderId} />
    </div>
  )
}
