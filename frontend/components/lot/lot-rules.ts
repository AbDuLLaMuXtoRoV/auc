import type { Auction } from "@/lib/api/types"

/**
 * Lot sahifasidagi auksion qoidalari (backend konstantalari bilan bir xil).
 * Server baribir o'zi tekshiradi — bu yerda faqat UI'da oldindan ko'rsatish uchun.
 */

/** bid_service.TYPO_WARNING_MULTIPLIER — joriy narxdan shuncha barobar ko'p taklif shubhali. */
export const TYPO_WARNING_MULTIPLIER = 3

/** Soft-close oynasi: tugashga shundan kam qolganda taklifni qaytarib bo'lmaydi. */
export const RETRACT_CUTOFF_SECONDS = 120

/**
 * Server qabul qiladigan eng kichik keyingi taklif (tiyin, number).
 * `minimum_next_bid` qadam jadvalini hisobga oladi; eski backend javobida
 * u bo'lmasa — oddiy `current_price + minimum_bid_increment` ga qaytamiz.
 */
export function minNextBidTiyin(auction: Auction): number {
  const server = Number(auction.minimum_next_bid)
  if (auction.minimum_next_bid != null && Number.isFinite(server) && server > 0) {
    return server
  }
  return Number(auction.current_price) + Number(auction.minimum_bid_increment)
}

/** Taklif joriy narxdan 3 barobardan ko'pmi (xato terilgan bo'lishi mumkin). */
export function isSuspiciouslyHigh(amountTiyin: number, auction: Auction): boolean {
  const current = Number(auction.current_price)
  return current > 0 && amountTiyin > current * TYPO_WARNING_MULTIPLIER
}
