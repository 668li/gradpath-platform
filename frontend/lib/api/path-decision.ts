import { request } from "./client";
import type {
  DecisionEngineInput,
  DecisionEngineResponse,
} from "@/types/path-comparison";

const BASE = "/api/path-decision";

export const pathDecisionApi = {
  /** 输入学生档案，生成三路对比（含证据溯源） */
  analyze: (input: DecisionEngineInput) =>
    request<DecisionEngineResponse>(BASE + "/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  /** 获取用户的历史三路对比记录 */
  getHistory: () =>
    request<DecisionEngineResponse[]>(BASE + "/history"),
};
