import { request, buildQuery } from "./client";

export interface OutcomeReportCreate {
  outcome_type: string;
  target_school?: string;
  target_major?: string;
  actual_school?: string;
  actual_major?: string;
  score_total?: number;
  score_politics?: number;
  score_english?: number;
  score_major1?: number;
  score_major2?: number;
  admission_path?: string;
  year: number;
  confidence_before?: number;
  satisfaction_after?: number;
  what_i_would_do_differently?: string;
  advice_for_others?: string;
  is_public?: string;
}

export interface OutcomeReport {
  id: string;
  user_id: string;
  outcome_type: string;
  target_school?: string;
  target_major?: string;
  actual_school?: string;
  actual_major?: string;
  score_total?: number;
  score_politics?: number;
  score_english?: number;
  score_major1?: number;
  score_major2?: number;
  admission_path: string;
  year: number;
  confidence_before?: number;
  satisfaction_after?: number;
  what_i_would_do_differently?: string;
  advice_for_others?: string;
  is_public: string;
  created_at?: string;
}

export interface OutcomeStats {
  school: string;
  major: string;
  total_outcomes: number;
  acceptance_rate?: number;
  avg_score_total?: number;
  score_distribution: Record<string, number>;
  path_breakdown: Record<string, number>;
  common_reflections: string[];
}

export interface OutcomeReportListResponse {
  items: OutcomeReport[];
  total: number;
}

export const outcomeReportApi = {
  submit: (data: OutcomeReportCreate) =>
    request<OutcomeReport>("/api/outcome-report/submit", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getMine: () =>
    request<OutcomeReportListResponse>("/api/outcome-report/mine"),

  getBySchool: (schoolName: string, major?: string, year?: number) =>
    request<OutcomeReportListResponse>(
      `/api/outcome-report/school/${encodeURIComponent(schoolName)}${buildQuery({ major, year })}`,
    ),

  getStats: (schoolName: string, major: string) =>
    request<OutcomeStats>(
      `/api/outcome-report/stats/${encodeURIComponent(schoolName)}/${encodeURIComponent(major)}`,
    ),

  getLandingWall: (params?: {
    school?: string;
    major?: string;
    year?: number;
    page?: number;
    page_size?: number;
  }) =>
    request<OutcomeReportListResponse>(
      `/api/outcome-report/landing-wall${buildQuery((params as Record<string, string | number | undefined>) || {})}`,
    ),
};
