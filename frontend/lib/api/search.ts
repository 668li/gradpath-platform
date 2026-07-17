import { request, buildQuery } from "./client";

// ===== 全局搜索 =====
export const searchApi = {
  search: (params: {
    q: string;
    type?: string;
    page?: number;
    page_size?: number;
  }) =>
    request<{
      query: string;
      type: string;
      total: number;
      page: number;
      page_size: number;
      results: Array<{
        id: string;
        type: string;
        title: string;
        content: string;
        highlight?: string;
        score: number;
        metadata?: Record<string, unknown>;
      }>;
    }>(`/api/search${buildQuery(params as Record<string, string | number | undefined | null>)}`),
  webSearch: (q: string) =>
    request<unknown>(`/api/ai/agent/web-search?q=${encodeURIComponent(q)}`),
};