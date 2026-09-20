export type HypothesisStatus = "open" | "validated" | "invalidated" | "superseded";
export type EvidenceSourceType = "official" | "dataset" | "peer" | "user" | "research" | "other";
export type EvidenceStance = "supports" | "refutes" | "neutral";

export interface DecisionHypothesis {
  id: string;
  user_id: string;
  decision_id: string;
  statement: string;
  importance: number;
  confidence: number;
  status: HypothesisStatus;
  verification_question: string | null;
  validation_action: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DecisionEvidence {
  id: string;
  user_id: string;
  decision_id: string;
  hypothesis_id: string | null;
  title: string;
  claim: string;
  source_url: string | null;
  source_type: EvidenceSourceType;
  reliability: number;
  stance: EvidenceStance;
  observed_on: string | null;
  excerpt: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface EvidenceReadiness {
  decision_id: string;
  hypotheses_total: number;
  hypotheses_with_evidence: number;
  hypotheses_unverified: number;
  evidence_total: number;
  evidence_supporting: number;
  evidence_refuting: number;
  evidence_neutral: number;
  coverage: number;
}
export interface EvidenceImportResult {
  decision_id: string;
  imported: number;
  skipped_duplicates: number;
  provider: string;
  notes: string[];
}
