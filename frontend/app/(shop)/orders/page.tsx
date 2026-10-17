import { OrdersView } from "@/components/order/orders-view"

export const metadata = {
  title: "Buyurtmalarim — Bazart",
}

export default function OrdersPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <OrdersView />
    </div>
  )
}
