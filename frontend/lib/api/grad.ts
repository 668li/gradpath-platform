import type { GradYanzhaoProgram } from "@/types";
import { request, buildQuery } from "./client";

// ===== 考研作战室 =====
export const gradIntelApi = {
  // 研招网真实数据（条件账本 target-condition-card.tsx 的核心消费者，勿删）
  listYanzhaoPrograms: (params?: {
    university_name?: string;
    major_name?: string;
    department?: string;
    degree_type?: string;
    year?: number;
    limit?: number;
    offset?: number;
  }) =>
    request<GradYanzhaoProgram[]>(
      `/api/grad-intel/yanzhao-programs${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
};

// ===== 考研可视化 =====
export const gradVisualizationApi = {
  getCrawlerQuality: () =>
    request<{
      total_runs: number;
      success_runs: number;
      failed_runs: number;
      success_rate: number;
      total_fetched: number;
      total_stored: number;
      total_duplicates: number;
      dedup_rate: number;
      store_rate: number;
      total_errors: number;
    }>("/api/grad-intel/visualization/crawler-quality"),
};
