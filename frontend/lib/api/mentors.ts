import type { GrowthPatternResponse } from "@/types";
import { request } from "./client";

// ===== 护城河功能：成长模式智能 =====
export const growthPatternsApi = {
  analyze: () => request<any>("/api/growth-patterns/analyze"),
  history: () => request<{ items: any[] }>("/api/growth-patterns/history"),
};
