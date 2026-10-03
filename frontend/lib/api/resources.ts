// 资源导航 API（RN-2，2026-10-03：资源导航聚合中心）
import { buildQuery, request } from "./client";

export interface ResourceSource {
  title: string;
  url: string;
  http_status?: number;
  page_title?: string;
  stars?: number;
  pushed_at?: string;
  license?: string;
  verdict: string;
  checked_at: string;
  note?: string;
}

export interface ResourceLink {
  id: string;
  name: string;
  url: string;
  track: string;
  category: string;
  note: string;
  risk_note: string | null;
  copyright_tier: "original" | "caution" | string;
  status: string;
  pending_review: boolean;
  user_approved: boolean;
  added_via: string;
  sources: ResourceSource[];
  recently_added: boolean;
}

export interface ResourceListResponse {
  total: number;
  items: ResourceLink[];
  active_count: number;
  pending_count: number;
}

export const RESOURCE_CATEGORY_LABELS: Record<string, string> = {
  kaoyan_resources: "考研干货",
  official: "官方入口",
  employment: "就业求职",
  open_source: "开源精选",
  tool: "工具",
};

export const resourcesApi = {
  list: (params?: { track?: string; category?: string; q?: string }) =>
    request<ResourceListResponse>(`/api/resources${buildQuery(params ?? {})}`),
};
