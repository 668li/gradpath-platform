// 复盘中心类型定义（对齐后端 app/schemas/review.py）

/** 复盘类型枚举 */
export type ReviewType = "daily" | "weekly" | "monthly" | "milestone";

/** 复盘状态枚举 */
export type ReviewStatus = "DRAFT" | "PENDING" | "COMPLETED" | "FAILED";

/** AI 复盘状态枚举 */
export type AIReviewStatus = "PENDING" | "COMPLETED" | "FAILED";

/** 创建复盘记录请求（user_id 由登录态 token 推断） */
export interface ReviewCreateRequest {
  review_type: ReviewType;
  /** 复盘周期开始；格式 年-月-日 */
  period_start: string;
  /** 复盘周期结束；格式 年-月-日 */
  period_end: string;
  /** 复盘内容；长度 ≤ 5000 */
  content: string;
  /** 关联行动 ID 列表（落库时转换为 {"action_ids": [...]} JSONB） */
  action_refs?: number[];
  /** 主观评分；范围 1~5 */
  mood_score?: number | null;
}

/** 复盘记录 VO */
export interface ReviewVO {
  id: number;
  user_id: string;
  review_type: ReviewType;
  period_start: string;
  period_end: string;
  content: string;
  /** 关联行动引用（JSONB） */
  action_refs: Record<string, unknown> | null;
  mood_score: number | null;
  status: ReviewStatus;
  created_time: string;
}

/** 复盘详情 VO = ReviewVO + AI 分析字段 */
export interface ReviewDetailVO extends ReviewVO {
  ai_summary: string | null;
  ai_insights: Record<string, unknown> | null;
  ai_suggestions: Record<string, unknown> | null;
  /** 不确定性评分；0.0~1.0 */
  uncertainty_score: number | null;
}

/** 复盘列表分页响应 */
export interface ReviewPageResponse {
  items: ReviewVO[];
  total: number;
}

/** 触发 AI 复盘分析请求 */
export interface AIReviewRequest {
  review_id: number;
  /** 关注维度；默认全维度 */
  focus_areas?: unknown[];
  /** LLM 温度；默认 0.3 */
  temperature?: number;
}

/** AI 复盘结果 VO */
export interface AIReviewVO {
  review_id: number;
  summary: string;
  /** 洞察列表（每条含 insight + evidence） */
  insights: unknown[];
  suggestions: unknown[];
  uncertainty_score: number;
  status: AIReviewStatus;
  created_at: string;
}
