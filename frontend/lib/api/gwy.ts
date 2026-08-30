import type {
  GwyPositionListResponse,
  GwyPositionResponse,
  GwyPositionStatsResponse,
  GwyProvincePositionListResponse,
  GwyScoreLineListResponse,
  GwyScoreLineStatsResponse,
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
 * 国考进面分数线 API（公开只读）。
 *
 * 对应后端 /api/gwy-score-lines：2026 国考面试名单按职位聚合的进面最低分
 * （首批 / 调剂 / 补充录用）。通过 position_code 与职位表关联。
 */
export const gwyScoreLinesApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    year?: number;
    batch?: string;
    position_code?: string;
    q?: string;
  }) =>
    request<GwyScoreLineListResponse>(
      `/api/gwy-score-lines${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),

  stats: (params?: { year?: number }) =>
    request<GwyScoreLineStatsResponse>(
      `/api/gwy-score-lines/stats${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
};

/**
 * 省考职位 API（公开只读）。
 *
 * 对应后端 /api/gwy-province-positions：各省考试录用公务员职位表（首例广东 2026）。
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
