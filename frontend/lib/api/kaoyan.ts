import type {
  PaginatedResponse,
  ExperiencePostResponse,
  ExperiencePostCreate,
  QAResponse,
  QACreate,
  QAAnswerResponse,
  QAAnswerCreate,
  KaoyanNewsListResponse,
  KaoyanNewsResponse,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 考研社区交流系统 =====
export const kaoyanCommunityApi = {
  // --- 经验贴 ---
  experiencePosts: {
    list: (params?: {
      page?: number;
      page_size?: number;
      category?: string;
      tag?: string;
      status?: string;
      search?: string;
    }) =>
      request<PaginatedResponse<ExperiencePostResponse>>(
        `/api/kaoyan/experience-posts${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
      ),
    get: (id: string) => request<ExperiencePostResponse>(`/api/kaoyan/experience-posts/${id}`),
    create: (body: ExperiencePostCreate) =>
      request<ExperiencePostResponse>("/api/kaoyan/experience-posts", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    update: (id: string, body: Partial<ExperiencePostCreate>) =>
      request<ExperiencePostResponse>(`/api/kaoyan/experience-posts/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    delete: (id: string) =>
      request<void>(`/api/kaoyan/experience-posts/${id}`, { method: "DELETE" }),
    like: (id: string) =>
      request<{ message: string; like_count: number }>(`/api/kaoyan/experience-posts/${id}/like`, {
        method: "POST",
      }),
  },

  // --- 问答 ---
  qa: {
    list: (params?: {
      page?: number;
      page_size?: number;
      tag?: string;
      status?: string;
      search?: string;
      is_resolved?: boolean;
    }) =>
      request<PaginatedResponse<QAResponse>>(
        `/api/kaoyan/qa${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
      ),
    get: (id: string) => request<QAResponse>(`/api/kaoyan/qa/${id}`),
    create: (body: QACreate) =>
      request<QAResponse>("/api/kaoyan/qa", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    update: (id: string, body: Partial<QACreate>) =>
      request<QAResponse>(`/api/kaoyan/qa/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    delete: (id: string) =>
      request<void>(`/api/kaoyan/qa/${id}`, { method: "DELETE" }),
    createAnswer: (questionId: string, body: QAAnswerCreate) =>
      request<QAAnswerResponse>(`/api/kaoyan/qa/${questionId}/answers`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    updateAnswer: (answerId: string, body: QAAnswerCreate) =>
      request<QAAnswerResponse>(`/api/kaoyan/qa/answers/${answerId}`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    acceptAnswer: (answerId: string) =>
      request<QAResponse>(`/api/kaoyan/qa/answers/${answerId}/accept`, {
        method: "POST",
      }),
    likeAnswer: (answerId: string) =>
      request<{ message: string; like_count: number }>(`/api/kaoyan/qa/answers/${answerId}/like`, {
        method: "POST",
      }),
  },
};

// ===== 考研资讯 =====
export const kaoyanNewsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    category?: string;
    search?: string;
  }) =>
    request<KaoyanNewsListResponse>(
      `/api/kaoyan-news${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<KaoyanNewsResponse>(`/api/kaoyan-news/${id}`),
};