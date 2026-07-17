import type {
  StudyPlan,
  StudyPlanCreate,
  StudyPlanUpdate,
  LearningResource,
  LearningResourceCreate,
  LearningResourceUpdate,
} from "@/types";
import { request, buildQuery } from "./client";

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

// ===== 学习资源 =====
export const learningResourceApi = {
  list: (params?: {
    subject?: string;
    difficulty?: string;
    resource_type?: string;
  }) =>
    request<LearningResource[]>(
      `/api/learning-resources${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<LearningResource>(`/api/learning-resources/${id}`),
  create: (body: LearningResourceCreate) =>
    request<LearningResource>("/api/learning-resources", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: LearningResourceUpdate) =>
    request<LearningResource>(`/api/learning-resources/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  delete: (id: string) =>
    request<void>(`/api/learning-resources/${id}`, { method: "DELETE" }),
};