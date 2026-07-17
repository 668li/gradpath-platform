import type {
  ReportDetail,
  ReportListResponse,
  PipelineStats,
  DataSourceResponse,
  DataSourceCreate,
  Company,
  SalaryBenchmark,
  MarketDataItem,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 数据管道 =====
export const pipelineApi = {
  // 接入
  ingestUrl: (body: { school_slug: string; year: number; url: string }) =>
    request<ReportDetail>("/api/pipeline/ingest/url", {
      method: "POST",
      body: JSON.stringify({ ...body, source_type: "crawl" }),
    }),

  ingestFile: (file: File, schoolSlug: string, year: number) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("school_slug", schoolSlug);
    formData.append("year", String(year));
    return request<ReportDetail>("/api/pipeline/ingest/file", {
      method: "POST",
      body: formData,
      headers: {}, // 让浏览器自动设置 Content-Type
    });
  },

  ingestApi: (body: { school_slug: string; year: number; api_source_id: string }) =>
    request<ReportDetail>("/api/pipeline/ingest/api", {
      method: "POST",
      body: JSON.stringify({ ...body, source_type: "api" }),
    }),

  // 报告管理
  reports: (params?: { status?: string; page?: number; page_size?: number }) =>
    request<ReportListResponse>(
      `/api/pipeline/reports${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),

  reportDetail: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}`),

  deleteReport: (id: string) =>
    request<void>(`/api/pipeline/reports/${id}`, { method: "DELETE" }),

  reparse: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}/reparse`, {
      method: "POST",
    }),

  publish: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}/publish`, {
      method: "POST",
    }),

  stats: () => request<PipelineStats>("/api/pipeline/stats"),

  // 数据源管理
  sources: () => request<DataSourceResponse[]>("/api/pipeline/sources"),

  createSource: (body: DataSourceCreate) =>
    request<DataSourceResponse>("/api/pipeline/sources", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateSource: (id: string, body: Partial<DataSourceCreate>) =>
    request<DataSourceResponse>(`/api/pipeline/sources/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteSource: (id: string) =>
    request<void>(`/api/pipeline/sources/${id}`, { method: "DELETE" }),
};

// ===== 外部数据 =====
export const externalDataApi = {
  companies: (params?: { name?: string; industry?: string }) =>
    request<Company[]>(
      `/api/companies${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  salaryBenchmarks: (params?: { company?: string; position?: string; city?: string }) =>
    request<SalaryBenchmark[]>(
      `/api/salary-benchmarks${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  marketData: (params?: { category?: string; year?: number; industry?: string }) =>
    request<MarketDataItem[]>(
      `/api/market-data${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
};