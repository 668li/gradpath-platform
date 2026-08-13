/** 失败案例库 API 客户端 — 对冲幸存者偏差。 */
import type {
  FailureCaseResponse,
  FailureCaseListResponse,
  FailureCaseStatsResponse,
  FailureCaseCreate,
} from "@/types/failure-case";
import { request, buildQuery } from "./client";

export const failureCaseApi = {
  /** 获取已审核案例列表（公开） */
  list: (params?: {
    path_type?: string;
    stage?: string;
    page?: number;
    size?: number;
  }) =>
    request<FailureCaseListResponse>(
      `/api/failure-cases${buildQuery(
        (params as Record<string, string | number | undefined | null>) || {},
      )}`,
    ),

  /** 获取案例详情（公开，自动增加浏览数） */
  get: (id: string) => request<FailureCaseResponse>(`/api/failure-cases/${id}`),

  /** 分享失败案例（需登录，匿名存储） */
  create: (body: FailureCaseCreate) =>
    request<FailureCaseResponse>("/api/failure-cases", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** 标记有帮助（需登录） */
  markHelpful: (id: string) =>
    request<{ helpful_count: number }>(
      `/api/failure-cases/${id}/helpful`,
      { method: "POST" },
    ),

  /** 获取统计信息（公开） */
  stats: () => request<FailureCaseStatsResponse>("/api/failure-cases/stats"),
};
