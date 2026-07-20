import { request, buildQuery } from "./client";

export interface RAGSearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  source?: string;
  url?: string;
  metadata?: Record<string, unknown>;
}

export interface RAGSearchResponse {
  query: string;
  results: RAGSearchResult[];
  total: number;
}

export const ragSearchApi = {
  search: (body: { query: string; top_k?: number; filters?: Record<string, unknown> }) =>
    request<RAGSearchResponse>("/api/rag/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  searchGet: (params: { query: string; top_k?: number }) =>
    request<RAGSearchResponse>(
      `/api/rag/search${buildQuery((params as Record<string, string | number | undefined | null>) || {})}`,
    ),
};
