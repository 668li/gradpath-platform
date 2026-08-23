// 多路径 What-If 对比相关类型定义
// 与后端 app/schemas/path_comparison.py 对齐

export type PathType =
  | "kaoyan"
  | "employment"
  | "civil_service"
  | "big_tech"
  | "startup"
  | "phd_abroad"
  | string;

export type RiskLevel = "low" | "medium" | "high";

export interface PathInput {
  path_type: PathType;
  target_role: string;
}

/** 单条证据 — 每个数字的溯源（source_url 或来源说明） */
export interface EvidenceItem {
  label: string;
  value: string;
  source_url: string | null;
  note?: string | null;
}

export interface PathMetrics {
  path_type: PathType;
  target_role: string;
  income_1y: string;
  income_3y: string;
  income_5y: string;
  risk_level: RiskLevel;
  risk_description: string;
  growth_score: number;
  time_cost_months: number;
  match_score: number;
  match_description: string;
  pros: string[];
  cons: string[];
  /** 决策引擎扩展：每条指标的溯源证据（老接口为空数组） */
  evidence?: EvidenceItem[];
}

export interface ComparisonResponse {
  id: string;
  metrics: PathMetrics[];
  recommendation: string;
  created_at: string;
}

/** 三路对比决策引擎输入 — 用户学生档案 */
export interface DecisionEngineInput {
  major: string;
  region?: string;
  school_tier?: string;
  graduation_year?: number;
}

/** 三路对比决策引擎响应 */
export interface DecisionEngineResponse {
  id: string;
  metrics: PathMetrics[];
  recommendation: string;
  input: Record<string, string | number>;
  created_at: string;
}
