/** Hududlar (viloyat) va tumanlar — ochiq, auth talab qilinmaydi. */
import { apiFetch } from "@/lib/api/client";

export interface Region {
  id: number;
  name_uz: string;
  name_ru: string;
  code: string;
}

export interface District {
  id: number;
  region_id: number;
  name_uz: string;
  name_ru: string;
}

export function listRegions(): Promise<Region[]> {
  return apiFetch<Region[]>("/regions", { auth: false });
}

export function listDistricts(regionId: number): Promise<District[]> {
  return apiFetch<District[]>(`/regions/${regionId}/districts`, { auth: false });
}
