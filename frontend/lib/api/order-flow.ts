/**
 * Buyurtma + escrow toʻlov + topshirish (handover) oqimi uchun API funksiyalari.
 *
 * Backend shartnomasiga mos (field nomlari va pul = TIYIN string aynan):
 *   - orders.py       GET /orders/buyer, /orders/seller, /orders/{id}
 *   - payments.py     POST /payments/holds, /payments/{id}/capture,
 *                     /payments/{id}/release, GET /payments/orders/{order_id}
 *   - handovers.py    POST /handovers, /handovers/{order_id}/confirm,
 *                     GET /handovers/{order_id}
 *
 * Escrow oqimi (PAYMENTS.md 4-bo'lim):
 *   Order(pending_payment)
 *     -> buyer create_hold  -> Payment(held), Order(pickup_pending)
 *     -> seller create_handover -> kod beriladi
 *     -> buyer confirm_handover(kod) -> capture (server-side) -> Payment(released), Order(completed)
 */

import { apiFetch, ApiError } from "@/lib/api/client";
import type { Order, PaymentStatus } from "@/lib/api/types";

// --- Turlar (backend sxemalarini aks ettiradi) ------------------------------

/** app/models/enums.py -> HandoverMethod */
export type HandoverMethod = "local_meetup" | "delivery";

/** app/models/enums.py -> HandoverStatus */
export type HandoverStatus = "pending" | "completed" | "failed";

/**
 * app/schemas/payment.py -> PaymentRead.
 * MUHIM: amount/premium/total — TIYIN, JSON'da STRING.
 */
export interface Payment {
  id: number;
  order_id: number;
  buyer_id: number;
  /** tiyin (string) — lot yakuniy narxi */
  amount: string;
  /** tiyin (string) — xaridor mukofoti (8%) */
  premium: string;
  /** tiyin (string) — amount + premium, escrow'da bloklanadigan summa */
  total: string;
  currency: string;
  status: PaymentStatus;
  provider: string;
  provider_payment_id: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * app/schemas/handover.py -> HandoverRead.
 * `code` faqat sotuvchiga (yoki adminga) qaytariladi; xaridor uchun null.
 */
export interface Handover {
  id: number;
  order_id: number;
  method: HandoverMethod;
  status: HandoverStatus;
  meet_address: string | null;
  confirmed_at: string | null;
  created_at: string;
  /** Topshirish kodi — egalik dalili. Faqat sotuvchida koʻrinadi. */
  code: string | null;
}

// --- Buyurtmalar ------------------------------------------------------------

/** GET /orders/buyer — joriy foydalanuvchi xaridor boʻlgan buyurtmalar. */
export function buyerOrders(): Promise<Order[]> {
  return apiFetch<Order[]>("/orders/buyer");
}

/** GET /orders/seller — joriy foydalanuvchi sotuvchi boʻlgan buyurtmalar. */
export function sellerOrders(): Promise<Order[]> {
  return apiFetch<Order[]>("/orders/seller");
}

/** GET /orders/{id} — bitta buyurtma (egalik tekshiruvi server tomonda). */
export function getOrder(id: number): Promise<Order> {
  return apiFetch<Order>(`/orders/${id}`);
}

// --- Escrow toʻlov ----------------------------------------------------------

/**
 * POST /payments/holds — escrow hold yaratadi (PSP kartada mablagʻni bloklaydi).
 *
 * Summa serverdan (order.final_price + xaridor mukofoti) hisoblanadi — klientdan
 * EMAS. `idempotency_key` klientdan (UUID) keladi va PSP chaqiruviga ham uzatiladi:
 * takroriy soʻrov ikki marta hold yaratmaydi.
 */
export function createHold(params: {
  order_id: number;
  idempotency_key: string;
  provider?: string;
  currency?: string;
}): Promise<Payment> {
  return apiFetch<Payment>("/payments/holds", {
    method: "POST",
    body: {
      order_id: params.order_id,
      idempotency_key: params.idempotency_key,
      provider: params.provider ?? "mock",
      currency: params.currency ?? "UZS",
    },
  });
}

/**
 * POST /payments/{id}/capture — bloklangan mablagʻni sotuvchiga oʻtkazadi.
 *
 * Odatda UI buni TOʻGʻRIDAN-TOʻGʻRI chaqirmaydi: handover tasdiqlash (buyer)
 * server tomonda capture'ni ishga tushiradi. Toʻliqlik uchun shu yerda.
 */
export function capturePayment(
  paymentId: number,
  idempotencyKey: string
): Promise<Payment> {
  return apiFetch<Payment>(`/payments/${paymentId}/capture`, {
    method: "POST",
    body: { idempotency_key: idempotencyKey },
  });
}

/**
 * POST /payments/{id}/release — hold'ni bekor qiladi (pul xaridorda qoladi).
 *
 * FAQAT admin (nizo qarori) chaqira oladi — UI'dagi xaridor/sotuvchi emas.
 */
export function releaseHold(
  paymentId: number,
  idempotencyKey: string
): Promise<Payment> {
  return apiFetch<Payment>(`/payments/${paymentId}/release`, {
    method: "POST",
    body: { idempotency_key: idempotencyKey },
  });
}

/**
 * GET /payments/orders/{order_id} — buyurtmaning oxirgi toʻlovi.
 * Toʻlov hali yaratilmagan boʻlsa backend 404 qaytaradi -> null.
 */
export function getOrderPayment(orderId: number): Promise<Payment | null> {
  return apiFetch<Payment>(`/payments/orders/${orderId}`).catch(nullOn404);
}

// --- Topshirish (handover) --------------------------------------------------

/**
 * POST /handovers — sotuvchi topshirishni boshlaydi va tasdiqlash kodini oladi.
 * Order PICKUP_PENDING (pul held) boʻlishi shart. Idempotent: mavjud handover
 * qaytariladi, kod qayta generatsiya qilinmaydi.
 */
export function createHandover(params: {
  order_id: number;
  method?: HandoverMethod;
  meet_address?: string | null;
}): Promise<Handover> {
  return apiFetch<Handover>("/handovers", {
    method: "POST",
    body: {
      order_id: params.order_id,
      method: params.method ?? "local_meetup",
      meet_address: params.meet_address ?? null,
    },
  });
}

/**
 * POST /handovers/{order_id}/confirm — xaridor uchrashuvda olgan kodni kiritadi.
 * Kod toʻgʻri boʻlsa server capture'ni ishga tushiradi (pul sotuvchiga),
 * order COMPLETED boʻladi. Javobda kod xaridorga koʻrsatilmaydi (null).
 */
export function confirmHandover(
  orderId: number,
  code: string
): Promise<Handover> {
  return apiFetch<Handover>(`/handovers/${orderId}/confirm`, {
    method: "POST",
    body: { code },
  });
}

/**
 * GET /handovers/{order_id} — buyurtmaning handoveri.
 * Hali yaratilmagan boʻlsa backend 404 qaytaradi -> null.
 */
export function getHandover(orderId: number): Promise<Handover | null> {
  return apiFetch<Handover>(`/handovers/${orderId}`).catch(nullOn404);
}

/** 404 -> null, boshqa xatoliklar qayta otiladi (mavjud emas != xatolik). */
function nullOn404(error: unknown): null {
  if (error instanceof ApiError && error.status === 404) return null;
  throw error;
}
