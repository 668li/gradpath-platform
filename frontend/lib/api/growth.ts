import { request } from "./client";
import type {
  GrowthArchiveVO,
  GrowthStatsVO,
  GrowthTrajectoryCreateRequest,
  GrowthTrajectoryListResponse,
  GrowthTrajectoryVO,
} from "@/types/growth-center";

const BASE = "/api/growth";

/** 成长档案中心 v1 client */
export const growthApi = {
  /** 获取成长轨迹时间轴 */
  getTrajectory: () =>
    request<GrowthTrajectoryListResponse>(`${BASE}/trajectory`),

  /** 记录成长轨迹事件（source_event_id 幂等，重复丢弃） */
  createTrajectory: (body: GrowthTrajectoryCreateRequest) =>
    request<GrowthTrajectoryVO>(`${BASE}/trajectory`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** 获取档案聚合（缺失时自动聚合生成） */
  getArchive: () => request<GrowthArchiveVO>(`${BASE}/archive`),

  /** 手动触发档案聚合刷新 */
  refreshArchive: () =>
    request<GrowthArchiveVO>(`${BASE}/archive/refresh`, { method: "PUT" }),

  /** 获取实时成长统计（跨表聚合） */
  getStats: () => request<GrowthStatsVO>(`${BASE}/stats`),
};
