import { request } from "./client";
import type {
  DecisionEngineInput,
  DecisionEngineResponse,
  DecisionOutcomeSubmit,
} from "@/types/path-comparison";

const BASE = "/api/path-decision";

export const pathDecisionApi = {
  /** 输入学生档案（含个人条件），生成三路对比（含证据溯源） */
  analyze: (input: DecisionEngineInput) =>
    request<DecisionEngineResponse>(BASE + "/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  /** 获取用户的历史三路对比记录 */
  getHistory: () =>
    request<DecisionEngineResponse[]>(BASE + "/history"),

  /** 结果回传：记录「当时选了哪条路、结果如何」 */
  submitOutcome: (id: string, payload: DecisionOutcomeSubmit) =>
    request<DecisionEngineResponse>(`${BASE}/${id}/outcome`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};
