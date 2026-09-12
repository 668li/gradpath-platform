/** 目标拆解器 API 客户端 —— 行动任务中心 #14（福格微行动） */
import { request } from "./client";

export interface GoalStep {
  day_number: number;
  title: string;
  description: string;
  estimated_minutes: number;
  anchor: string;
  task_type: string;
  fogg: { m: number; a: number; p: number };
}

export interface GoalDecomposePreview {
  goal: string;
  path_type: string;
  steps: GoalStep[];
  note: string;
}

export interface GoalCommitResult {
  plan_id: string;
  target_role: string;
  task_count: number;
  redirect: string;
}

export const goalDecomposeApi = {
  preview: (body: { goal: string; path_type: string; motivation: number }) =>
    request<GoalDecomposePreview>("/api/goal-decompose/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  commit: (body: { goal: string; path_type: string; steps: GoalStep[] }) =>
    request<GoalCommitResult>("/api/goal-decompose/commit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
