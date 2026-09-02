import { request, buildQuery } from "./client";

/** 专业前景 — 按专业聚合真实就业/升学/考公数据 */

export interface MajorListItem {
  name: string;
  category: string;
  source: "mapped" | "grad_intel";
  has_grad_intel: boolean;
}

export interface IndustrySalary {
  industry: string;
  year: number;
  salary_non_private: number;
  salary_private: number | null;
  vs_national: number;
  source: string;
}

export interface PositionSalary {
  position: string;
  salary_median: number;
  salary_min: number;
  salary_max: number;
  cities: string[];
  source: string;
  year: number;
}

export interface ProspectCompany {
  name: string;
  industry: string;
  size: string;
  headquarters: string | null;
}

export interface GradPath {
  school_name: string;
  school_tier: string;
  major_name: string;
  year: number;
  admission_ratio: string;
  score_line: number | null;
  push_ratio: string;
  background_discrimination: string;
  first_choice_protection: string;
  outgoing_note: string | null;
  outgoing_risk: "friendly" | "acceptable" | "careful" | "high" | null;
}

export interface CivilServiceInfo {
  level: "high" | "medium" | "low";
  label: string;
  note: string;
}

export interface MajorProspect {
  major: string;
  matched_major: string;
  exact_match: boolean;
  category: string;
  industries: IndustrySalary[];
  positions: PositionSalary[];
  companies: ProspectCompany[];
  grad_paths: GradPath[];
  grad_personalized: boolean;
  civil_service: CivilServiceInfo;
  related_majors: string[];
  tier_fact: string;
  data_notes: string[];
}

/** 本科出身层次（用于升学路径个性化）。专科手动选档，不建专科院校库。 */
export const OUTGOING_TIERS = ["985", "211", "双一流", "一本", "二本", "专科"] as const;
export type OutgoingTier = (typeof OUTGOING_TIERS)[number];

// ===== 专业前景 =====
export const majorProspectApi = {
  majors: () => request<MajorListItem[]>("/api/major-prospects/majors"),
  outgoingTiers: () => request<{ tiers: string[] }>("/api/major-prospects/outgoing-tiers"),
  detail: (major: string, outgoingTier?: OutgoingTier | null) =>
    request<MajorProspect>(
      `/api/major-prospects/detail${buildQuery({
        major,
        ...(outgoingTier ? { outgoing_tier: outgoingTier } : {}),
      })}`,
    ),
};
