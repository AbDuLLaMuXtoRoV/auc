/**
 * Kuzatuv ro'yxati (watchlist). Backend: app/api/v1/endpoints/watchlist.py.
 * Qo'shish idempotent — takror qo'shish xato bermaydi.
 */
import { apiFetch } from "@/lib/api/client";

/** WatchlistRead sxemasi. */
export interface WatchlistEntry {
  id: number;
  auction_id: number;
  created_at: string;
}

export function listWatchlist(): Promise<WatchlistEntry[]> {
  return apiFetch<WatchlistEntry[]>("/watchlist");
}

export function addToWatchlist(auctionId: number): Promise<WatchlistEntry> {
  return apiFetch<WatchlistEntry>("/watchlist", { body: { auction_id: auctionId } });
}

/** 204 qaytaradi (body yo'q). */
export function removeFromWatchlist(auctionId: number): Promise<void> {
  return apiFetch<void>(`/watchlist/${auctionId}`, { method: "DELETE" });
}
