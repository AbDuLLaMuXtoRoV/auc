/**
 * JWT tokenlarni saqlash — localStorage (client-only).
 * client.ts va auth store shu modul orqali ishlaydi (aylanma import bo'lmasin).
 */

const KEY = "bazart-auth";

export type Tokens = { access: string; refresh: string };

let cache: Tokens | null = null;

function read(): Tokens | null {
  if (typeof window === "undefined") return null;
  if (cache) return cache;
  try {
    const raw = localStorage.getItem(KEY);
    cache = raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    cache = null;
  }
  return cache;
}

export function getAccessToken(): string | null {
  return read()?.access ?? null;
}

export function getRefreshToken(): string | null {
  return read()?.refresh ?? null;
}

export function setTokens(tokens: Tokens): void {
  cache = tokens;
  if (typeof window !== "undefined") {
    localStorage.setItem(KEY, JSON.stringify(tokens));
  }
}

export function clearTokens(): void {
  cache = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem(KEY);
  }
}
