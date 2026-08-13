import { request } from "./client";
import type {
  MicroActionPlanCreate,
  MicroActionPlanResponse,
  MicroActionTaskResponse,
  TaskCompleteRequest,
} from "@/types/micro-action";

const BASE = "/api/micro-actions";

export const microActionApi = {
  /** 创建 7 天微行动计划，自动生成 7 个任务 */
  createPlan: (body: MicroActionPlanCreate) =>
    request<MicroActionPlanResponse>(BASE + "/plans", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** 获取当前活跃 plan，没有时返回 null */
  getCurrentPlan: () =>
    request<MicroActionPlanResponse | null>(BASE + "/plans/current"),

  /** 获取指定 plan（必须属于当前用户） */
  getPlan: (planId: string) =>
    request<MicroActionPlanResponse>(`${BASE}/plans/${planId}`),

  /** 完成任务：标记完成 + 生成 AI 洞察 + 检查 plan 完成状态 */
  completeTask: (taskId: string, body: TaskCompleteRequest) =>
    request<MicroActionTaskResponse>(`${BASE}/tasks/${taskId}/complete`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** 跳过任务：仅标记状态 */
  skipTask: (taskId: string) =>
    request<MicroActionTaskResponse>(`${BASE}/tasks/${taskId}/skip`, {
      method: "POST",
    }),

  /** 获取用户所有 plan 历史 */
  getHistory: () =>
    request<MicroActionPlanResponse[]>(BASE + "/history"),
};
