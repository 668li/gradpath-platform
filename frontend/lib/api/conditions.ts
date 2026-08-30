/**
 * 报考条件账本 API — 技能树转型：目标职位条件清单 + 勾选进度 + 完成率。
 * 对应后端 /api/condition-checklist（规则生成，零录入，每条带职位表字段溯源）。
 */
import { request } from "./client";
import type {
  ConditionChecklistResponse,
  ConditionStatusUpdateRequest,
} from "@/types";

export const conditionChecklistApi = {
  getChecklist: (positionId: string, source: "national" | "province" = "national") =>
    request<ConditionChecklistResponse>(
      `/api/condition-checklist/${positionId}?source=${source}`,
    ),

  updateStatus: (data: ConditionStatusUpdateRequest) =>
    request<ConditionChecklistResponse>(`/api/condition-checklist/status`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};
