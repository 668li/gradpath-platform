import type {
  StudyPlan,
  StudyPlanCreate,
  StudyPlanUpdate,
} from "@/types";
import { request } from "./client";

// ===== 学习计划 =====
export const studyPlanApi = {
  list: () => request<StudyPlan[]>("/api/study-plans"),
  get: (id: string) => request<StudyPlan>(`/api/study-plans/${id}`),
  create: (body: StudyPlanCreate) =>
    request<StudyPlan>("/api/study-plans", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: StudyPlanUpdate) =>
    request<StudyPlan>(`/api/study-plans/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    request<void>(`/api/study-plans/${id}`, { method: "DELETE" }),
};
