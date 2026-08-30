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

/** 三路对比决策引擎输入 — 用户学生档案 + 个人条件包（决策飞轮可报边界） */
export interface DecisionEngineInput {
  major: string;
  region?: string;
  school_tier?: string;
  graduation_year?: number;
  /** 应届状态：应届 / 非应届 */
  fresh_status?: string;
  /** 政治面貌：中共党员 / 党员或团员 / 群众 */
  party_status?: string;
  /** 最高学历：博士 / 硕士 / 本科 / 大专 */
  education?: string;
  /** 是否满足基层工作经历 / 服务基层项目要求 */
  has_grassroots?: boolean;
  /** 性别：男 / 女 */
  gender?: string;
  /** 行测+申论预估总分（200 分制） */
  estimated_score?: number;
  /** 考研初试模考估分（500 分制），用于院校劝退判定 */
  kaoyan_estimated_score?: number;
}

/** 可报岗位示例 — 考公岗位级分析的展示单位 */
export interface TopPosition {
  dept_name: string;
  position_name: string;
  work_location?: string | null;
  recruit_count?: number | null;
  min_score?: number | null;
  score_label: string;
  source_url?: string | null;
}

/** 劝退卡 — 诚实拒绝：预估分显著低于进面线的岗位（结论/依据/替代/置信标签） */
export interface AvoidPosition {
  dept_name: string;
  position_name: string;
  verdict: string;
  basis: string;
  confidence: string;
  alternatives: string[];
  source_url?: string | null;
}

/** 全站结果回传统计（匿名聚合，互惠展示用） */
export interface OutcomeStats {
  total_outcomes: number;
  by_status: Record<string, number>;
  by_selected_path: Record<string, number>;
}

/** 考公岗位级分析 — 个人可报清单 + 进面线分层 */
export interface PositionAnalysis {
  eligible_count: number;
  province_count: number;
  score_band: string;
  personalized_level?: string | null;
  tier_summary?: string | null;
  top_positions: TopPosition[];
  /** 劝退卡（预估分显著低于进面线的岗位，含替代建议） */
  avoid_positions?: AvoidPosition[];
  /** 可报岗位中触发劝退档的数量 */
  discouraged_count?: number;
  notes: string[];
}

/** 考研院校劝退卡 — 模考估分显著低于复试线的院校（结论/依据/替代/置信） */
export interface AvoidSchool {
  university_name: string;
  major_name?: string | null;
  verdict: string;
  basis: string;
  confidence: string;
  alternatives: string[];
  source_url?: string | null;
}

/** 考研院校级竞争力 — 竞争档位 + 隐性情报 */
export interface SchoolCompetitionItem {
  university_name: string;
  major_name: string;
  degree_type?: string | null;
  year?: number | null;
  score_line?: number | null;
  ratio?: string | null;
  competition: string;
  intel?: string | null;
  source_url?: string | null;
}

/** 考研院校级分析 */
export interface SchoolAnalysis {
  matched_school_count: number;
  coverage_note: string;
  items: SchoolCompetitionItem[];
  /** 劝退卡（模考估分显著低于复试线的院校，含替代建议；未填估分则为空） */
  avoid_schools?: AvoidSchool[];
}

/** 结果回传信息（响应内嵌） */
export interface DecisionOutcomeInfo {
  selected_path?: string | null;
  selected_label?: string | null;
  outcome_status?: string | null;
  actual_outcome?: string | null;
  satisfaction?: number | null;
  reviewed_at?: string | null;
}

/** 结果回传请求体 */
export interface DecisionOutcomeSubmit {
  selected_path: "kaoyan" | "civil_service" | "employment";
  selected_label?: string;
  outcome_status: "pending" | "following" | "achieved" | "abandoned";
  actual_outcome?: string;
  satisfaction?: number;
}

/** 三路对比决策引擎响应 */
export interface DecisionEngineResponse {
  id: string;
  metrics: PathMetrics[];
  recommendation: string;
  input: Record<string, string | number | boolean>;
  created_at: string;
  /** 考公岗位级分析（基于个人条件） */
  position_analysis?: PositionAnalysis | null;
  /** 考研院校级分析 */
  school_analysis?: SchoolAnalysis | null;
  /** 结果回传信息（已记录时为非空） */
  outcome?: DecisionOutcomeInfo | null;
}
