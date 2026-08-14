import { request, buildQuery } from "./client";
import type {
  AIReviewVO,
  ReviewCreateRequest,
  ReviewDetailVO,
  ReviewPageResponse,
  ReviewVO,
} from "@/types/review-center";

const BASE = "/api/reviews";

/** 生成幂等键：同一操作重复提交时后端返回首次结果（去重保护） */
function idemKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** 复盘中心 v1 client */
export const reviewsApi = {
  /** 创建复盘记录（X-Idempotency-Key 幂等） */
  create: (body: ReviewCreateRequest) =>
    request<ReviewVO>(BASE, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "X-Idempotency-Key": idemKey() },
    }),

  /** 读取复盘详情（含 AI 分析字段） */
  get: (reviewId: number) => request<ReviewDetailVO>(`${BASE}/${reviewId}`),

  /** 复盘列表（分页） */
  list: (page = 1, size = 20) =>
    request<ReviewPageResponse>(`${BASE}${buildQuery({ page, size })}`),

  /** 触发 AI 复盘分析（LLM 不可用走模板降级；已分析返回既有结果） */
  aiAnalyze: (reviewId: number, body?: { focus_areas?: unknown[]; temperature?: number }) =>
    request<AIReviewVO>(`${BASE}/${reviewId}/ai-analyze`, {
      method: "POST",
      body: JSON.stringify({ review_id: reviewId, ...body }),
    }),

  /** 获取 AI 复盘结果 */
  aiResult: (reviewId: number) =>
    request<AIReviewVO>(`${BASE}/${reviewId}/ai-result`),
};
