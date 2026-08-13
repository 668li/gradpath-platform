import { request, buildQuery } from "./client";

// ===== 同路人洞察（创意功能）=====

export interface PeerDistributionItem {
  destination_type: string;
  label: string;
  count: number;
  percent: number;
}

export interface PeerAdvice {
  advice: string;
  target_school: string | null;
  year: number | null;
  satisfaction: number | null;
}

export interface PeerMirrorResponse {
  has_data: boolean;
  peer_count: number;
  stage_label: string;
  distribution: PeerDistributionItem[];
  success_rate: number | null;
  peer_advice: PeerAdvice | null;
}

export interface ProcrastinationItem {
  decision_id: string;
  destination_type: string;
  destination_label: string;
  days_pending: number;
  lost_prep_hours: number;
  urgency: "critical" | "high" | "medium" | "low";
  message: string;
  confidence: number;
}

export interface ProcrastinationResponse {
  has_pending: boolean;
  pending_count: number;
  total_stale_days: number;
  total_lost_hours: number;
  items: ProcrastinationItem[];
}

export interface DarkKnowledgeGapItem {
  id: string;
  title: string;
  content_preview: string;
  stage: string;
  category: string;
  read_by_peers: number;
  common_misconception: string | null;
}

export interface DarkKnowledgeGapResponse {
  has_gap: boolean;
  gap_count: number;
  items: DarkKnowledgeGapItem[];
}

export interface RegretLesson {
  text: string;
  target_school: string | null;
  target_major: string | null;
  year: number | null;
  score_total: number | null;
  satisfaction_after: number | null;
  confidence_before: number | null;
}

export interface RegretLessonGroup {
  outcome_type: string;
  label: string;
  tone: "success" | "mixed" | "caution" | "neutral";
  lessons: RegretLesson[];
}

export interface RegretLessonsResponse {
  has_lessons: boolean;
  group_count: number;
  groups: RegretLessonGroup[];
}

export const peerInsightsApi = {
  mirror: () => request<PeerMirrorResponse>("/api/peer-insights/mirror"),
  procrastination: () =>
    request<ProcrastinationResponse>("/api/peer-insights/procrastination"),
  darkKnowledgeGap: (limit = 5) =>
    request<DarkKnowledgeGapResponse>(
      `/api/peer-insights/dark-knowledge-gap${buildQuery({ limit })}`,
    ),
  regretLessons: (limitPerType = 2) =>
    request<RegretLessonsResponse>(
      `/api/peer-insights/regret-lessons${buildQuery({ limit_per_type: limitPerType })}`,
    ),
};
