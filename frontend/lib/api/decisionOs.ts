import { request } from "./client";

// Decision OS（D9）类型与 API —— 后端 app/api/decision_os.py 对齐。
// 类型在本模块自包含，不进 @/types（避免与并行会话的 types 大文件冲突）。

export type HypothesisImportance = "critical" | "high" | "supporting";
export type HypothesisStatus = "untested" | "supporting" | "refuted" | "obsolete";
export type EvidenceStance = "supporting" | "contradicting" | "neutral";
export type EvidenceVerificationStatus =
  | "internal_unverified"
  | "externally_verified"
  | "contradicted"
  | "stale"
  | "unverifiable";
export type ActionStatus = "todo" | "doing" | "done" | "skipped";
export type ActionResultStance = "hypothesis_supported" | "hypothesis_weakened" | "inconclusive";
export type OutcomeKind = "direct" | "partial" | "unobservable" | "counterfactual_unknown";
export type MatchStatus = "matched" | "partial" | "missed" | "unknown";

export interface DraftHypothesis {
  statement: string;
  importance: HypothesisImportance;
  impact?: string | null;
}

export interface StructuredDraft {
  question: string;
  context?: string | null;
  options: string[];
  constraints: string[];
  desired_outcome?: string | null;
  hypotheses: DraftHypothesis[];
  evidence_needs: string[];
  ai_used: boolean;
}

export interface DecisionRow {
  id: string;
  question?: string | null;
  context?: string | null;
  constraints: string[];
  options: string[];
  desired_outcome?: string | null;
  destination_type: string;
  status: string;
  assumptions: string[];
  confidence: number;
  created_at: string;
}

export interface HypothesisCard {
  id: string;
  decision_id: string;
  statement: string;
  importance: HypothesisImportance;
  confidence: number;
  status: HypothesisStatus;
  impact?: string | null;
  result?: string | null;
  created_at: string;
  evidence_count: number;
  supporting: number;
  contradicting: number;
  neutral: number;
}

export interface EvidenceRow {
  id: string;
  decision_id: string | null;
  hypothesis_id: string | null;
  claim: string;
  source?: string | null;
  source_url?: string | null;
  source_type: string;
  reliability: string;
  stance: EvidenceStance;
  provider?: string | null;
  verification_status: EvidenceVerificationStatus;
  verification_source?: string | null;
  verified_on?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface ActionRow {
  id: string;
  decision_id: string;
  hypothesis_id: string | null;
  title: string;
  uncertainty?: string | null;
  expected_information_gain?: string | null;
  status: ActionStatus;
  result?: string | null;
  result_stance?: ActionResultStance | null;
  due_date?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface OutcomeRow {
  id: string;
  decision_id: string;
  kind: OutcomeKind;
  summary: string;
  observed_on?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface ReflectionRow {
  id: string;
  decision_id: string;
  prediction_error?: string | null;
  wrong_assumption?: string | null;
  omitted_factor?: string | null;
  lesson?: string | null;
  match_status: MatchStatus;
  new_principle?: string | null;
  ai_summary?: string | null;
  created_at: string;
}

export interface DecisionCard {
  decision: DecisionRow;
  hypotheses: HypothesisCard[];
  evidence: EvidenceRow[];
  actions: ActionRow[];
  outcomes: OutcomeRow[];
  reflections: ReflectionRow[];
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});

export const decisionOsApi = {
  structure: (rawText: string) =>
    request<StructuredDraft>("/api/decision-os/structure", json({ raw_text: rawText })),

  confirmDraft: (draft: StructuredDraft, destinationType: string) =>
    request<DecisionCard>("/api/decision-os/decisions/confirm-draft", {
      ...json({ draft, destination_type: destinationType }),
    }),

  card: (decisionId: string) =>
    request<DecisionCard>(`/api/decision-os/decisions/${decisionId}/card`),

  addHypothesis: (
    decisionId: string,
    body: { statement: string; importance: HypothesisImportance; impact?: string },
  ) => request<HypothesisCard>(`/api/decision-os/decisions/${decisionId}/hypotheses`, json(body)),

  addEvidence: (
    decisionId: string,
    body: {
      claim: string;
      stance: EvidenceStance;
      provider?: string;
      source_url?: string;
      source_type?: string;
    },
  ) => request<EvidenceRow>(`/api/decision-os/decisions/${decisionId}/evidence`, json(body)),

  addHypothesisEvidence: (
    hypothesisId: string,
    body: { claim: string; stance: EvidenceStance; provider?: string; source_url?: string },
  ) => request<EvidenceRow>(`/api/decision-os/hypotheses/${hypothesisId}/evidence`, json(body)),

  verifyEvidence: (
    evidenceId: string,
    body: { verification_status: EvidenceVerificationStatus; verification_source: string },
  ) => request<EvidenceRow>(`/api/decision-os/evidence/${evidenceId}/verify`, json(body)),

  addAction: (
    decisionId: string,
    body: {
      title: string;
      hypothesis_id?: string | null;
      uncertainty?: string;
      expected_information_gain?: string;
    },
  ) => request<ActionRow>(`/api/decision-os/decisions/${decisionId}/actions`, json(body)),

  completeAction: (
    actionId: string,
    body: {
      result: string;
      result_stance: ActionResultStance;
      hypothesis_status_update?: HypothesisStatus | null;
    },
  ) => request<ActionRow>(`/api/decision-os/actions/${actionId}/complete`, json(body)),

  addOutcome: (
    decisionId: string,
    body: { kind: OutcomeKind; summary: string; observed_on?: string },
  ) => request<OutcomeRow>(`/api/decision-os/decisions/${decisionId}/outcomes`, json(body)),

  addReflection: (
    decisionId: string,
    body: {
      lesson?: string;
      wrong_assumption?: string;
      prediction_error?: string;
      omitted_factor?: string;
      match_status: MatchStatus;
      new_principle?: string;
    },
  ) => request<ReflectionRow>(`/api/decision-os/decisions/${decisionId}/reflections`, json(body)),
};
