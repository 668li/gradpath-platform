"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

/** 对比清单上限 */
export const GWY_COMPARE_MAX = 6;

interface GwyCompareState {
  /** 已选职位 id 列表（保序） */
  ids: string[];
  toggle: (id: string) => void;
  remove: (id: string) => void;
  clear: () => void;
}

/**
 * 国考职位对比清单（纯前端状态，localStorage 持久化）。
 *
 * 用 skipHydration 避免 SSR 与客户端首帧不一致（服务端 ids 恒为 []，
 * 客户端在 useEffect 里手动 rehydrate 后才会填充，见检索页/对比页）。
 */
export const useGwyCompareStore = create<GwyCompareState>()(
  persist(
    (set, get) => ({
      ids: [],
      toggle: (id) => {
        const ids = get().ids;
        if (ids.includes(id)) {
          set({ ids: ids.filter((x) => x !== id) });
        } else if (ids.length < GWY_COMPARE_MAX) {
          set({ ids: [...ids, id] });
        }
      },
      remove: (id) => set({ ids: get().ids.filter((x) => x !== id) }),
      clear: () => set({ ids: [] }),
    }),
    {
      name: "gwy-compare-ids",
      skipHydration: true,
      partialize: (s) => ({ ids: s.ids }),
      storage: createJSONStorage(() =>
        typeof window !== "undefined"
          ? localStorage
          : // SSR 时无 localStorage，提供空存储避免读写报错
            { getItem: () => null, setItem: () => {}, removeItem: () => {} },
      ),
    },
  ),
);
