import type {
  GwyPositionListResponse,
  GwyPositionResponse,
  GwyPositionStatsResponse,
  GwyProvincePositionListResponse,
} from "@/types";
import { request, buildQuery } from "./client";

/**
 * 国考职位 API（公开只读）。
 *
 * 对应后端 /api/gwy-positions：2026 国考招考简章官方职位表。
 * 支持关键词/学历/政治面貌/机构层级/考试类别/省份前缀/职位代码/年份筛选 + 分页。
 */
export const gwyPositionsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    q?: string;
    education_req?: string;
    political_status?: string;
    org_level?: string;
    exam_category?: string;
    province?: string;
    position_code?: string;
    year?: number;
  }) =>
    request<GwyPositionListResponse>(
      `/api/gwy-positions${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),

  get: (id: string) => request<GwyPositionResponse>(`/api/gwy-positions/${id}`),

  stats: (params?: { year?: number }) =>
    request<GwyPositionStatsResponse>(
      `/api/gwy-positions/stats${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
};

/**
 * 省考职位 API（公开只读）。
 *
 * 对应后端 /api/gwy-province-positions：各省考试录用公务员职位表（首例广东 2026）。
 * 2026-09-25 ponytail 瘦身：gwyScoreLinesApi 删除——后端 API 层已下线（模型保留），
 * 前端无任何组件调用。
 */
export const provincePositionsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    q?: string;
    province?: string;
    education_req?: string;
    exam_region?: string;
    fresh_grad_only?: string;
    sheet_name?: string;
    year?: number;
  }) =>
    request<GwyProvincePositionListResponse>(
      `/api/gwy-province-positions${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
};
