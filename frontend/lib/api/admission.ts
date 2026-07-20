import { request, buildQuery } from "./client";

export interface PredictResponse {
  school: string;
  major: string;
  probability: number;
  risk_level: string;
  suggestion?: string;
  factors?: Record<string, unknown>;
}

export interface HistoryResponse {
  school: string;
  major: string;
  records: Array<{
    year: number;
    score: number;
    admission_count?: number;
    min_rank?: number;
  }>;
}

export const admissionApi = {
  predict: (body: { school: string; major: string; score?: number; rank?: number }) =>
    request<PredictResponse>("/api/admission/predict", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  history: (school: string, major: string) =>
    request<HistoryResponse>(
      `/api/admission/history/${encodeURIComponent(school)}/${encodeURIComponent(major)}`,
    ),
};
