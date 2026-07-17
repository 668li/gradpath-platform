import type {
  CareerPlan,
  MilestoneLog,
  ReminderItem,
  DailyFocusItem,
  CareerProfile,
  CareerProfileCreate,
  PlanTemplate,
} from "@/types";
import { request } from "./client";

// ===== 职业规划 =====
export const careerPlansApi = {
  list: () => request<CareerPlan[]>("/api/career-plans"),
  get: (id: string) => request<CareerPlan>(`/api/career-plans/${id}`),
  updateMilestone: (planId: string, milestoneIdx: number, status: string) =>
    request<CareerPlan>(
      `/api/career-plans/${planId}/milestones/${milestoneIdx}`,
      { method: "PATCH", body: JSON.stringify({ status }) },
    ),
  addLog: (planId: string, idx: number, content: string) =>
    request<MilestoneLog>(
      `/api/career-plans/${planId}/milestones/${idx}/logs`,
      { method: "POST", body: JSON.stringify({ content }) },
    ),
  listLogs: (planId: string, idx: number) =>
    request<MilestoneLog[]>(
      `/api/career-plans/${planId}/milestones/${idx}/logs`,
    ),
  deleteLog: (planId: string, logId: string) =>
    request<void>(`/api/career-plans/${planId}/logs/${logId}`, {
      method: "DELETE",
    }),
  getReminders: () => request<ReminderItem[]>("/api/career-plans/reminders"),
  getDailyFocus: () => request<DailyFocusItem[]>("/api/career-plans/daily-focus"),
};

// ===== 用户职业画像 =====
export const careerProfileApi = {
  get: () => request<CareerProfile | null>("/api/career-profile"),
  create: (body: CareerProfileCreate) =>
    request<CareerProfile>("/api/career-profile", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (body: Partial<CareerProfileCreate>) =>
    request<CareerProfile>("/api/career-profile", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};

// ===== 规划模板 =====
export const planTemplatesApi = {
  list: () => request<PlanTemplate[]>("/api/plan-templates"),
  get: (id: string) => request<PlanTemplate>(`/api/plan-templates/${id}`),
};