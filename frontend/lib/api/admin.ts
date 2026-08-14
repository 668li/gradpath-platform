/**
 * 管理端 API — 社区治理（用户管理 + 举报处理）。
 * 所有请求走 request()（自动携带 Authorization），后端要求 is_admin。
 */
import { buildQuery, request } from "./client";

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  nickname?: string | null;
  school?: string | null;
  major?: string | null;
  graduation_year?: number | null;
  is_admin: boolean;
  status: "active" | "banned";
  banned_at?: string | null;
  ban_reason?: string | null;
  created_at: string;
}

export interface AdminUserListResponse {
  total: number;
  items: AdminUser[];
}

export interface BanResponse {
  id: string;
  status: string;
  banned_at?: string | null;
  ban_reason?: string | null;
  message: string;
}

export type ReportTargetType =
  | "post"
  | "experience_post"
  | "comment"
  | "qa"
  | "qa_answer"
  | "user";

export interface ReportItem {
  id: string;
  reporter_id: string;
  target_type: ReportTargetType;
  target_id: string;
  reason: string;
  detail?: string | null;
  status: "pending" | "processed" | "rejected";
  processed_by?: string | null;
  processed_at?: string | null;
  processed_note?: string | null;
  created_at: string;
}

export interface ReportListResponse {
  total: number;
  items: ReportItem[];
}

export interface ReportCreateRequest {
  target_type: ReportTargetType;
  target_id: string;
  reason: string;
  detail?: string;
}

export interface ReportProcessRequest {
  action: "processed" | "rejected";
  ban_author?: boolean;
  ban_reason?: string;
  note?: string;
}

export interface ReportProcessResult {
  report_id: string;
  status: string;
  message: string;
}

/** 用户管理（管理端） */
export const adminApi = {
  listUsers(params: {
    keyword?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<AdminUserListResponse> {
    return request(
      `/api/admin/users${buildQuery({ ...params, page_size: params.page_size ?? 20 })}`,
    );
  },
  banUser(userId: string, reason: string): Promise<BanResponse> {
    return request(`/api/admin/users/${userId}/ban`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },
  unbanUser(userId: string): Promise<BanResponse> {
    return request(`/api/admin/users/${userId}/unban`, { method: "POST" });
  },
};

/** 举报（用户提交 + 管理端处理） */
export const reportsApi = {
  list(params: {
    status?: string;
    target_type?: string;
    page?: number;
    page_size?: number;
  }): Promise<ReportListResponse> {
    return request(`/api/admin/reports${buildQuery(params)}`);
  },
  process(
    reportId: string,
    body: ReportProcessRequest,
  ): Promise<ReportProcessResult> {
    return request(`/api/admin/reports/${reportId}/process`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  create(body: ReportCreateRequest): Promise<ReportItem> {
    return request("/api/reports", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};
