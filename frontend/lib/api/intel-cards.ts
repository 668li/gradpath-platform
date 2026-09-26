// 门道卡 API（批次 B+：门道信息差·考研先行）
import { buildQuery, request } from "./client";

export interface IntelCardSource {
  title: string;
  url: string;
  supports?: string;
}

export interface IntelCard {
  id: string;
  track: string;
  category: "rule" | "circle" | "evidence" | string;
  question_id: string;
  question_text: string;
  title: string;
  conclusion: string;
  conditions: string;
  counterexample: string | null;
  confidence: "official" | "multi_source" | "single_source" | string;
  sources: IntelCardSource[];
  evidence_data: Record<string, unknown> | null;
  as_of: string;
}

export interface IntelCardListResponse {
  total: number;
  items: IntelCard[];
  covered_questions: number;
}

export interface IntelQuestionGroup {
  question_id: string;
  question_text: string;
  category: string;
  cards: IntelCard[];
}

export interface IntelQuestionListResponse {
  total: number;
  groups: IntelQuestionGroup[];
}

export const intelCardsApi = {
  list: (params?: { category?: string; q?: string }) =>
    request<IntelCardListResponse>(`/api/intel/cards${buildQuery(params ?? {})}`),

  byQuestion: (track = "kaoyan") =>
    request<IntelQuestionListResponse>(
      `/api/intel/cards/questions${buildQuery({ track })}`,
    ),
};
