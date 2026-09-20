import type {
  DecisionEvidence,
  DecisionHypothesis,
  EvidenceReadiness,
  EvidenceSourceType,
  EvidenceStance,
  HypothesisStatus,
} from "@/types/decision-evidence";
import { request } from "./client";

export interface HypothesisCreatePayload {
  statement: string;
  importance?: number;
  confidence?: number;
  status?: HypothesisStatus;
  verification_question?: string | null;
  validation_action?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EvidenceCreatePayload {
  hypothesis_id?: string | null;
  title: string;
  claim: string;
  source_url?: string | null;
  source_type?: EvidenceSourceType;
  reliability?: number;
  stance?: EvidenceStance;
  observed_on?: string | null;
  excerpt?: string | null;
  metadata?: Record<string, unknown>;
}

export const decisionEvidenceApi = {
  hypotheses: (decisionId: string) =>
    request<DecisionHypothesis[]>(`/api/decisions/${decisionId}/hypotheses`),

  createHypothesis: (decisionId: string, body: HypothesisCreatePayload) =>
    request<DecisionHypothesis>(`/api/decisions/${decisionId}/hypotheses`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateHypothesis: (decisionId: string, hypothesisId: string, body: Partial<HypothesisCreatePayload>) =>
    request<DecisionHypothesis>(`/api/decisions/${decisionId}/hypotheses/${hypothesisId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteHypothesis: (decisionId: string, hypothesisId: string) =>
    request<void>(`/api/decisions/${decisionId}/hypotheses/${hypothesisId}`, { method: "DELETE" }),

  evidence: (decisionId: string, hypothesisId?: string) =>
    request<DecisionEvidence[]>(`/api/decisions/${decisionId}/evidence${
      hypothesisId ? `?hypothesis_id=${encodeURIComponent(hypothesisId)}` : ""
    }`),

  createEvidence: (decisionId: string, body: EvidenceCreatePayload) =>
    request<DecisionEvidence>(`/api/decisions/${decisionId}/evidence`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateEvidence: (decisionId: string, evidenceId: string, body: Partial<EvidenceCreatePayload>) =>
    request<DecisionEvidence>(`/api/decisions/${decisionId}/evidence/${evidenceId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteEvidence: (decisionId: string, evidenceId: string) =>
    request<void>(`/api/decisions/${decisionId}/evidence/${evidenceId}`, {
      method: "DELETE",
    }),

  readiness: (decisionId: string) =>
    request<EvidenceReadiness>(`/api/decisions/${decisionId}/evidence-readiness`),
};