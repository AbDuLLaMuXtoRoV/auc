import { create } from "zustand";

import type { User } from "@/lib/api/types";
import * as api from "@/lib/api/endpoints";
import {
  setTokens,
  clearTokens,
  getAccessToken,
  getRefreshToken,
} from "@/lib/api/token";

type AuthStatus = "idle" | "authenticated" | "anonymous";

type AuthState = {
  user: User | null;
  status: AuthStatus;
  loadMe: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: "idle",

  loadMe: async () => {
    if (!getAccessToken()) {
      set({ status: "anonymous", user: null });
      return;
    }
    try {
      const user = await api.me();
      set({ user, status: "authenticated" });
    } catch {
      clearTokens();
      set({ user: null, status: "anonymous" });
    }
  },

  login: async (email, password) => {
    const token = await api.login(email, password);
    setTokens({ access: token.access_token, refresh: token.refresh_token });
    const user = await api.me();
    set({ user, status: "authenticated" });
  },

  loginWithGoogle: async (credential) => {
    const token = await api.googleLogin(credential);
    setTokens({ access: token.access_token, refresh: token.refresh_token });
    const user = await api.me();
    set({ user, status: "authenticated" });
  },

  register: async (email, password, fullName) => {
    await api.register({ email, password, full_name: fullName });
    const token = await api.login(email, password);
    setTokens({ access: token.access_token, refresh: token.refresh_token });
    const user = await api.me();
    set({ user, status: "authenticated" });
  },

  logout: async () => {
    try {
      await api.logout(getRefreshToken());
    } catch {
      // logout xatosi bo'lsa ham lokal tokenni tozalaymiz.
    }
    clearTokens();
    set({ user: null, status: "anonymous" });
  },
}));
