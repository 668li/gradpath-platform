import { request, buildQuery } from "./client";

export interface LearningMethod {
  id: string;
  title: string;
  summary: string;
  content: string;
  source: string;
  tags: string[];
  category: string;
  view_count: number;
  bookmark_count: number;
  created_at: string;
  updated_at: string;
  is_recommended?: boolean;
  reason?: string;
  score?: number;
}

export interface LearningMethodListResponse {
  items: LearningMethod[];
  total: number;
  page: number;
  page_size: number;
}

export interface LearningMethodTag {
  id: string;
  name: string;
  count: number;
}

export interface LearningMethodStats {
  category_counts: { category: string; count: number }[];
  total: number;
}

export const learningMethodsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    tag?: string;
    category?: string;
    search?: string;
  }) =>
    request<LearningMethodListResponse>(
      `/api/learning-methods${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),

  detail: (id: string) =>
    request<LearningMethod>(`/api/learning-methods/${id}`),

  tags: () =>
    request<LearningMethodTag[]>("/api/learning-methods/tags"),

  recommend: (limit = 5) =>
    request<LearningMethod[]>(
      `/api/learning-methods/recommend${buildQuery({ limit })}`,
    ),

  stats: () =>
    request<LearningMethodStats>("/api/learning-methods/stats"),

  bookmark: (id: string) =>
    request<{ bookmarked: boolean }>(`/api/learning-methods/${id}/bookmark`, {
      method: "POST",
    }),
};
