"use client";

import { create } from "zustand";
import { authApi, setToken, clearToken, getToken } from "@/lib/api";
import type { UserResponse } from "@/types";

interface AuthState {
  token: string | null;
  user: UserResponse | null;
  hydrated: boolean;
  setAuth: (token: string, user: UserResponse) => void;
  setToken: (token: string) => void;
  setUser: (user: UserResponse) => void;
  logout: () => void;
  fetchUser: () => Promise<UserResponse | null>;
  /** 从 localStorage 恢复 token（仅在客户端调用） */
  restore: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  // 初始值：SSR 与首次客户端渲染一致（均为 null），避免 hydration mismatch
  token: null,
  user: null,
  hydrated: false,
  setAuth: (token, user) => {
    setToken(token);
    set({ token, user });
  },
  setToken: (token) => {
    setToken(token);
    set({ token });
  },
  setUser: (user) => set({ user }),
  logout: () => {
    clearToken();
    set({ token: null, user: null });
  },
  fetchUser: async () => {
    const token = get().token || getToken();
    if (!token) return null;
    try {
      const user = await authApi.me();
      set({ user });
      return user;
    } catch {
      clearToken();
      set({ token: null, user: null });
      return null;
    }
  },
  restore: () => {
    // 仅在客户端执行，从 localStorage 读取 token
    const token = getToken();
    set({ token, hydrated: true });
  },
}));
