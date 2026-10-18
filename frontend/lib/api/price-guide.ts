/**
 * Telefon narx ko'rsatkichi API'si.
 *
 * Barcha narxlar — TIYIN (string), backend Koreya diler narxlarini (won) admin
 * belgilagan kurs bo'yicha so'mga o'girib beradi. Bu taxminiy baho — UI har doim
 * manba va kursni (`info`) ko'rsatadi.
 */

import { apiFetch } from "@/lib/api/client";
import type { DeviceDefect, DeviceGrade } from "@/lib/api/types";

export interface PriceGuideInfo {
  /** 1 won necha tiyin (855 = 8.55 so'm). */
  rate_tiyin_per_krw: number;
  /** Bozor tuzatmasi, basis points (+1500 = +15%). */
  market_adjust_bps: number;
  updated_at: string | null;
  source: string;
}

export interface DeviceModel {
  id: number;
  slug: string;
  brand: string;
  name: string;
  series: string;
  storages: string[];
}

export interface StoragePrices {
  storage: string;
  /** tiyin (string) yoki null — shu darajada baholanmaydi */
  a: string | null;
  a_minus: string | null;
  b_plus: string | null;
  b_minus: string | null;
  base: string | null;
}

export interface DeviceModelDetail extends DeviceModel {
  info: PriceGuideInfo;
  prices: StoragePrices[];
  /** nosozlik -> ajratma, tiyin (string) */
  deductions: Partial<Record<DeviceDefect, string>>;
  scrap: string | null;
}

export interface EstimateRequest {
  model_id: number;
  storage: string;
  grade?: DeviceGrade;
  battery_health?: number;
  defects?: DeviceDefect[];
}

export interface Estimate {
  model_id: number;
  model_name: string;
  storage: string;
  grade: DeviceGrade | null;
  /** tiyin (string) — ajratmalardan oldin */
  grade_price: string;
  battery_adjusted: boolean;
  deductions: { defect: DeviceDefect; amount: string }[];
  /** tiyin (string) — yakuniy taxminiy baho */
  estimate: string;
  floored_to_scrap: boolean;
  info: PriceGuideInfo;
}

export function getPriceGuide(): Promise<{ info: PriceGuideInfo; models: DeviceModel[] }> {
  return apiFetch(`/price-guide`, { auth: false });
}

export function getDeviceModel(slug: string): Promise<DeviceModelDetail> {
  return apiFetch<DeviceModelDetail>(`/price-guide/models/${encodeURIComponent(slug)}`, {
    auth: false,
  });
}

export function estimateDevice(payload: EstimateRequest): Promise<Estimate> {
  return apiFetch<Estimate>(`/price-guide/estimate`, { body: payload, auth: false });
}

// --- Admin -------------------------------------------------------------

export function getPriceGuideSettings(): Promise<PriceGuideInfo> {
  return apiFetch<PriceGuideInfo>(`/admin/price-guide/settings`);
}

export function updatePriceGuideSettings(payload: {
  rate_tiyin_per_krw: number;
  market_adjust_bps: number;
}): Promise<PriceGuideInfo> {
  return apiFetch<PriceGuideInfo>(`/admin/price-guide/settings`, { method: "PUT", body: payload });
}
