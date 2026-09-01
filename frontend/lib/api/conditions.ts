/**
 * 报考条件账本 API — 技能树转型：目标职位条件清单 + 勾选进度 + 完成率。
 * 对应后端 /api/condition-checklist（规则生成，零录入，每条带职位表字段溯源）。
 */
import { request } from "./client";
import type {
  ConditionChecklistResponse,
  ConditionStatusUpdateRequest,
  MyProfileSummary,
} from "@/types";

export const conditionChecklistApi = {
  getChecklist: (
    positionId: string,
    source: "national" | "province" | "kaoyan" = "national",
  ) =>
    request<ConditionChecklistResponse>(
      `/api/condition-checklist/${positionId}?source=${source}`,
    ),

  /** 我的条件账本结算：可报性结论 + 硬门槛/可补项未满足清单 */
  getProfileSummary: () =>
    request<MyProfileSummary>(`/api/condition-checklist/my-profile-summary`),

  updateStatus: (data: ConditionStatusUpdateRequest) =>
    request<ConditionChecklistResponse>(`/api/condition-checklist/status`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};
