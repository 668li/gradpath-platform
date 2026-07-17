import type {
  KnowledgeArticle,
  PaginatedResponse,
  KnowledgeArticleCreate,
  KnowledgeArticleUpdate,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 知识库 =====
export const knowledgeApi = {
  list: (params?: {
    category?: string;
    page?: number;
    page_size?: number;
  }) =>
    request<PaginatedResponse<KnowledgeArticle>>(
      `/api/knowledge${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<KnowledgeArticle>(`/api/knowledge/${id}`),
  search: (query: string) =>
    request<KnowledgeArticle[]>("/api/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  create: (body: KnowledgeArticleCreate) =>
    request<KnowledgeArticle>("/api/knowledge", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: KnowledgeArticleUpdate) =>
    request<KnowledgeArticle>(`/api/knowledge/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    request<void>(`/api/knowledge/${id}`, { method: "DELETE" }),
};