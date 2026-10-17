/**
 * Buyurtma / toʻlov / topshirish holatlarini oʻzbekcha yorliq va Badge'ga
 * moslaydi. Yagona manba — komponentlarda holat matni takrorlanmaydi.
 */

import type { OrderStatus, PaymentStatus } from "@/lib/api/types"
import type { HandoverStatus } from "@/lib/api/order-flow"
import { Badge } from "@/components/ui/badge"

type BadgeVariant =
  | "default"
  | "secondary"
  | "success"
  | "warning"
  | "sale"
  | "neutral"
  | "outline"

const ORDER_LABEL: Record<OrderStatus, string> = {
  pending_payment: "Toʻlov kutilmoqda",
  paid: "Toʻlangan",
  pickup_pending: "Topshirish kutilmoqda",
  completed: "Yakunlangan",
  cancelled: "Bekor qilingan",
}

const ORDER_VARIANT: Record<OrderStatus, BadgeVariant> = {
  pending_payment: "warning",
  paid: "secondary",
  pickup_pending: "default",
  completed: "success",
  cancelled: "neutral",
}

const PAYMENT_LABEL: Record<PaymentStatus, string> = {
  pending: "Kutilmoqda",
  processing: "Jarayonda",
  paid: "Toʻlangan",
  failed: "Muvaffaqiyatsiz",
  refunded: "Qaytarilgan",
  held: "Bloklangan (escrow)",
  released: "Sotuvchiga oʻtkazildi",
  cancelled_hold: "Blok bekor qilindi",
}

const PAYMENT_VARIANT: Record<PaymentStatus, BadgeVariant> = {
  pending: "warning",
  processing: "secondary",
  paid: "success",
  failed: "sale",
  refunded: "neutral",
  held: "default",
  released: "success",
  cancelled_hold: "neutral",
}

export function orderStatusLabel(status: OrderStatus): string {
  return ORDER_LABEL[status] ?? status
}

export function paymentStatusLabel(status: PaymentStatus): string {
  return PAYMENT_LABEL[status] ?? status
}

export function handoverStatusLabel(status: HandoverStatus): string {
  const map: Record<HandoverStatus, string> = {
    pending: "Kod berildi, tasdiq kutilmoqda",
    completed: "Tasdiqlangan",
    failed: "Bekor boʻldi",
  }
  return map[status] ?? status
}

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return <Badge variant={ORDER_VARIANT[status] ?? "outline"}>{orderStatusLabel(status)}</Badge>
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  return <Badge variant={PAYMENT_VARIANT[status] ?? "outline"}>{paymentStatusLabel(status)}</Badge>
}
