import { request } from "./client";
import type {
  PathInput,
  ComparisonResponse,
} from "@/types/path-comparison";

const BASE = "/api/path-comparison";

export const pathComparisonApi = {
  /** 提交 2-3 条路径生成量化对比 */
  compare: (paths: PathInput[]) =>
    request<ComparisonResponse>(BASE + "/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paths }),
    }),

  /** 获取用户的历史对比记录（按时间倒序） */
  getHistory: () =>
    request<ComparisonResponse[]>(BASE + "/history"),
};
