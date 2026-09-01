/**
 * 免费可报性预览 API — 免登录「先尝一口」的转化漏斗入口。
 *
 * 访客无需注册：搜职位/院校 → 勾身份字段 → 立即看到可报性判定。
 * 与登录后条件账本共用同一套后端判定（/api/condition-checklist/preview，
 * 无 get_current_user）。必须用 request()（不用 useApi/apiFetcher，
 * 后者 401 会强制跳登录，免登录页不可用）。
 */
import { request } from "./client";

export type PreviewExamSource = "national" | "province" | "kaoyan";

export interface ConditionPreviewRequest {
  exam_source: PreviewExamSource;
  position_ref: string;
  fresh_status?: string;
  party_status?: string;
  education?: string;
  has_grassroots?: boolean;
  gender?: string;
  estimated_score?: number;
  kaoyan_estimated_score?: number;
}

export interface ConditionBlockItem {
  key: string;
  label: string;
  reason: string;
}

export interface ConditionPreviewResponse {
  exam_source: string;
  position_ref: string;
  position_name?: string | null;
  dept_name?: string | null;
  /** national/province：能否报考；kaoyan 恒为 null */
  eligible?: boolean | null;
  blockers: ConditionBlockItem[];
  verdict_text?: string | null;
  // kaoyan 专用
  university_name?: string | null;
  major_name?: string | null;
  level?: string | null;
  total_score_line?: number | null;
  score_lines?: Record<string, number> | null;
}

export const conditionPreviewApi = {
  /** 免费可报性判定（免登录） */
  preview: (data: ConditionPreviewRequest) =>
    request<ConditionPreviewResponse>("/api/condition-checklist/preview", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
