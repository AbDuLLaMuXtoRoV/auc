/**
 * Huquqiy rozilik (consent) yozuvlari. Nizo chiqqanda "qaysi versiya qabul
 * qilingan" savoliga javob berish uchun har qabul versiyasi + IP bilan saqlanadi.
 */
import { apiFetch } from "@/lib/api/client";

export type ConsentDocumentType = "terms" | "privacy" | "auction_rules" | "public_offer";

/**
 * Joriy hujjatlar versiyasi. Hujjat matni o'zgarsa — shu qiymat ham o'zgaradi,
 * shunda foydalanuvchidan yangi versiyaga qayta rozilik so'raladi.
 */
export const LEGAL_VERSION = "2026-10";

export interface LegalConsent {
  id: number;
  document_type: ConsentDocumentType;
  version: string;
  accepted_at: string;
  ip: string | null;
}

export function recordConsent(
  documentType: ConsentDocumentType,
  version: string = LEGAL_VERSION
): Promise<LegalConsent> {
  return apiFetch<LegalConsent>("/legal/consent", {
    body: { document_type: documentType, version },
  });
}

export function listMyConsents(): Promise<LegalConsent[]> {
  return apiFetch<LegalConsent[]>("/legal/consents");
}

/** Berilgan hujjatlarning JORIY versiyasi qabul qilinganmi. */
export function hasConsented(
  consents: LegalConsent[],
  documents: ConsentDocumentType[],
  version: string = LEGAL_VERSION
): boolean {
  return documents.every((d) =>
    consents.some((c) => c.document_type === d && c.version === version)
  );
}
