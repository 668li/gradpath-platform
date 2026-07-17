import type { CrawlerInfo, CrawlerRun, PaginatedResponse } from "@/types";
import { request, buildQuery } from "./client";

// ===== 爬虫管理后台（admin-only） =====
export const crawlerApi = {
  /** 获取所有已注册爬虫列表 */
  list: () => request<CrawlerInfo[]>("/api/crawlers"),
  /** 触发指定爬虫运行 */
  run: (sourceName: string) =>
    request<CrawlerRun>("/api/crawlers/run", {
      method: "POST",
      body: JSON.stringify({ source_name: sourceName }),
    }),
  /** 获取爬取历史（分页） */
  runs: (page = 1, pageSize = 20) =>
    request<PaginatedResponse<CrawlerRun>>(
      `/api/crawlers/runs${buildQuery({ page: String(page), page_size: String(pageSize) })}`,
    ),
  /** 获取单次运行详情 */
  runDetail: (runId: string) =>
    request<CrawlerRun>(`/api/crawlers/runs/${runId}`),
};