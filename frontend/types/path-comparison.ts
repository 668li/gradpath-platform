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
}

export interface ComparisonResponse {
  id: string;
  metrics: PathMetrics[];
  recommendation: string;
  created_at: string;
}
