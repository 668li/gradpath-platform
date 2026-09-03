import type { PaginatedResponse } from "@/types";
import { request, buildQuery } from "./client";

// ===== 调研数据审核队列（admin-only） =====
// 审核链路统一走 t_review_queue_item：管理员在 /admin/research-queue
// 对采集条目（经验帖/考研资讯/暗知识）执行 通过/驳回/标记重复。

export interface ResearchQueueItem {
  queue_id: number;
  item_type: string; // external_research
  ref_item_id: number;
  biz_req_no: string;
  source_url: string;
  review_status: string; // PENDING / APPROVED / REJECTED / DUPLICATED
  reject_reason: string | null;
  reviewed_by: string | null;
  reviewed_time: string | null;
  created_time: string;

  // === t_external_research_item 关联详情 ===
  title: string;
  content: string;
  crawler_name: string;
  source_platform: string;
  credibility: string; // official_verified / user_reported / model_inferred
  external_meta: Record<string, unknown> | null;

  // === 风险信号（仅 PENDING 计算，已审完为 null）===
  risk_grade: "high" | "medium" | "low" | null;
  risk_score: number | null;
  risk_reasons: string[];
}

export interface ResearchQueueListResponse extends PaginatedResponse<ResearchQueueItem> {}

export interface QueueActionResponse {
  message: string;
  queue_id: number;
  review_status: string;
  ref_item_id: number;
  promoted: number;
}

export const researchQueueApi = {
  /** 待审核列表（支持 item_type / source_platform / review_status 过滤，分页） */
  list: (params: {
    item_type?: string;
    source_platform?: string;
    review_status?: string;
    page?: number;
    page_size?: number;
  }) =>
    request<ResearchQueueListResponse>(
      `/api/admin/research-queue/pending${buildQuery({
        item_type: params.item_type,
        source_platform: params.source_platform,
        review_status: params.review_status,
        page: String(params.page ?? 1),
        page_size: String(params.page_size ?? 20),
      })}`,
    ),
  /** 审核通过 → 落业务表（ExperiencePost/KaoyanNews/DarkKnowledge） */
  approve: (queueId: number, body?: { note?: string }) =>
    request<QueueActionResponse>(`/api/admin/research-queue/${queueId}/approve`, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  /** 驳回（可填原因） */
  reject: (queueId: number, body?: { reject_reason?: string }) =>
    request<QueueActionResponse>(`/api/admin/research-queue/${queueId}/reject`, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  /** 标记重复（可填重复来源 URL） */
  duplicate: (queueId: number, body?: { duplicate_of?: string }) =>
    request<QueueActionResponse>(`/api/admin/research-queue/${queueId}/duplicate`, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
};
