"use client";

import { create } from "zustand";
import { onboardingApi } from "@/lib/api";
import type { OnboardingRecord, OnboardingGetResponse } from "@/types";

interface OnboardingState {
  /** 是否已完成首次诊断 */
  completed: boolean | null; // null = 未加载
  record: OnboardingRecord | null;
  loading: boolean;
  /** 拉取最新 onboarding 状态 */
  refresh: () => Promise<OnboardingGetResponse>;
  /** 标记为已完成（生成诊断成功后调用） */
  markCompleted: (record: OnboardingRecord) => void;
  /** 跳过 onboarding 后调用 */
  markSkipped: () => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  completed: null,
  record: null,
  loading: false,
  refresh: async () => {
    set({ loading: true });
    try {
      const resp = await onboardingApi.get();
      set({
        completed: resp.completed,
        record: resp.onboarding,
        loading: false,
      });
      return resp;
    } catch {
      set({ loading: false });
      // 失败时默认未完成，让用户手动操作
      return { onboarding: null, completed: false };
    }
  },
  markCompleted: (record) => set({ record, completed: true }),
  markSkipped: () => set({ completed: true }),
}));
