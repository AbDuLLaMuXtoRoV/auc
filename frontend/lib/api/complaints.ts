/**
 * Shikoyatlar. Yaratish — har qanday kirgan foydalanuvchi; ro'yxat va holatni
 * o'zgartirish — faqat admin (backend 403 beradi).
 */
import { apiFetch } from "@/lib/api/client";

export type ComplaintTargetType = "item" | "user" | "auction" | "message" | "order";

export type ComplaintStatus = "open" | "reviewing" | "resolved" | "rejected";

/** ComplaintRead sxemasi. */
export interface Complaint {
  id: number;
  reporter_id: number;
  target_type: ComplaintTargetType;
  target_id: number;
  reason: string;
  description: string | null;
  status: ComplaintStatus;
  resolved_by_id: number | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ComplaintCreateInput {
  target_type: ComplaintTargetType;
  target_id: number;
  /** 1..200 belgi. */
  reason: string;
  /** <= 2000 belgi. */
  description?: string;
}

export function createComplaint(input: ComplaintCreateInput): Promise<Complaint> {
  return apiFetch<Complaint>("/complaints", { body: input });
}

/** Admin: shikoyatlar ro'yxati, ixtiyoriy holat filtri. */
export function listComplaints(status?: ComplaintStatus): Promise<Complaint[]> {
  return apiFetch<Complaint[]>(`/complaints${status ? `?status=${status}` : ""}`);
}

/** Admin: holatni o'zgartirish. resolved/rejected bo'lsa server resolved_at ni o'zi yozadi. */
export function updateComplaintStatus(id: number, status: ComplaintStatus): Promise<Complaint> {
  return apiFetch<Complaint>(`/complaints/${id}`, { method: "PATCH", body: { status } });
}
