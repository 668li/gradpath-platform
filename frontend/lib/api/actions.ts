import { request } from "./client";
import type {
  ActionCreateRequest,
  ActionListResponse,
  ActionUpdateRequest,
  ActionVO,
  ActionWeightListResponse,
  CheckinListResponse,
  CheckinRequest,
  CheckinVO,
  StreakVO,
} from "@/types/action-center";

const BASE = "/api/v1/actions";

/** 生成幂等键：同一操作重复提交时后端返回首次结果（去重保护） */
function idemKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** 行动任务中心 v1 client */
export const actionsApi = {
  /** 今日行动清单（按权重降序） */
  getToday: () => request<ActionListResponse>(`${BASE}/today`),

  /** 生成行动项（X-Idempotency-Key 幂等） */
  create: (body: ActionCreateRequest) =>
    request<ActionVO>(BASE, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "X-Idempotency-Key": idemKey() },
    }),

  /** 更新行动项（部分更新） */
  update: (actionId: number, body: ActionUpdateRequest) =>
    request<ActionVO>(`${BASE}/${actionId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  /** 行动打卡（X-Idempotency-Key 幂等） */
  checkin: (actionId: number, body: Omit<CheckinRequest, "action_id">) =>
    request<CheckinVO>(`${BASE}/${actionId}/checkin`, {
      method: "POST",
      body: JSON.stringify({ ...body, action_id: actionId }),
      headers: { "X-Idempotency-Key": idemKey() },
    }),

  /** 查询打卡历史 */
  getCheckins: (actionId: number) =>
    request<CheckinListResponse>(`${BASE}/${actionId}/checkins`),

  /** 查询连续天数（从未打卡返回 NEVER 占位） */
  getStreak: () => request<StreakVO>(`${BASE}/streaks`),

  /** 查询行动权重表（幂等种子保障） */
  getWeights: () => request<ActionWeightListResponse>(`${BASE}/weights`),
};
