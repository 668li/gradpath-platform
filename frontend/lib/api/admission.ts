import { request, buildQuery } from "./client";

export interface PredictFactor {
  factor: string;
  impact: string; // positive / negative / neutral
  weight: number;
}

export interface SimilarCase {
  user_score: number;
  outcome: string; // admitted / rejected / waitlist
}

export interface PredictResponse {
  school_name: string;
  major: string;
  probability: number;
  confidence: string; // high / medium / low
  factors: PredictFactor[];
  similar_cases: SimilarCase[];
  recommendation: string;
  risk_level: string; // low / medium / high
}

export interface HistoryResponse {
  school_name: string;
  major: string;
  records: Array<{
    year: number;
    total_score_line: number | null;
    enrollment_count: number | null;
    application_count: number | null;
    politics_score: number | null;
    foreign_language_score: number | null;
    business_1_score: number | null;
    business_2_score: number | null;
  }>;
  statistics: {
    year_span: string;
    data_points: number;
    avg_score: number | null;
    max_score: number | null;
    min_score: number | null;
    avg_admission_rate: number | null;
  };
}

export const admissionApi = {
  predict: (body: {
    school_name: string;
    major: string;
    user_score: number;
    user_gpa: number;
    user_university: string;
  }) =>
    request<PredictResponse>("/api/admission/predict", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  history: (school: string, major: string) =>
    request<HistoryResponse>(
      `/api/admission/history/${encodeURIComponent(school)}/${encodeURIComponent(major)}`,
    ),
};
