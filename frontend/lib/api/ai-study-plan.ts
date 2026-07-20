import { request } from "./client";

// ===== AI 学习计划 API =====
export interface GeneratePlanRequest {
  target_school: string;
  target_major: string;
  current_score: number;
  target_score: number;
  weak_subjects: string[];
  exam_date: string;
  study_hours_per_day: number;
}

export interface SubjectPlan {
  subject: string;
  daily_hours: number;
  tasks: string[];
}

export interface WeeklyPlan {
  week: number;
  subjects: SubjectPlan[];
  weekly_test: string;
  milestone: string;
}

export interface Phase {
  name: string;
  duration_days: number;
  weekly_plan: WeeklyPlan[];
  goals: string[];
}

export interface GeneratePlanResponse {
  total_days: number;
  target_school: string;
  target_major: string;
  current_score: number;
  target_score: number;
  phases: Phase[];
  daily_schedule: {
    morning: string;
    afternoon: string;
    evening: string;
  };
  tips: string[];
  ai_summary: string;
}

export interface SavedPlan {
  id: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  subjects: string[];
  progress: number;
  completed: boolean;
  created_at: string | null;
}

export interface PlanProgress {
  plan_id: string;
  title: string;
  progress: number;
  total_days: number;
  elapsed_days: number;
  remaining_days: number;
  start_date: string | null;
  end_date: string | null;
  is_on_track: boolean;
}

export const aiStudyPlanApi = {
  generate: (body: GeneratePlanRequest) =>
    request<GeneratePlanResponse>("/api/ai-study-plan/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  save: (planData: GeneratePlanRequest, generatedPlan: GeneratePlanResponse) =>
    request<{ id: string; message: string }>("/api/ai-study-plan/save", {
      method: "POST",
      body: JSON.stringify({ plan_data: planData, generated_plan: generatedPlan }),
    }),

  getMine: () => request<SavedPlan[]>("/api/ai-study-plan/mine"),

  getProgress: (planId: string) =>
    request<PlanProgress>(`/api/ai-study-plan/${planId}/progress`),

  updateProgress: (planId: string, week: number, completedTasks: string[]) =>
    request<{ progress: number; completed: boolean }>(
      `/api/ai-study-plan/${planId}/progress`,
      {
        method: "PUT",
        body: JSON.stringify({ week, completed_tasks: completedTasks }),
      }
    ),
};
