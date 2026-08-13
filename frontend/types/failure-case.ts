/** 失败案例库类型定义 — 对冲幸存者偏差的真实失败叙事。 */

export type FailureCasePathType =
  | "kaoyan"
  | "civil_service"
  | "employment"
  | "study_abroad";

export type FailureCaseStage =
  | "preparation"
  | "interview"
  | "final_year1"
  | "year2_plus";

export interface FailureCaseResponse {
  id: string;
  author_role: string;
  path_type: FailureCasePathType;
  stage: FailureCaseStage;
  title: string;
  story: string;
  lessons: string[];
  regrets: string[];
  what_would_i_do: string;
  helpful_count: number;
  view_count: number;
  created_at: string;
}

export interface FailureCaseListResponse {
  items: FailureCaseResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface FailureCaseStatsResponse {
  total: number;
  by_path: Record<string, number>;
  by_stage: Record<string, number>;
}

export interface FailureCaseCreate {
  author_role: string;
  path_type: FailureCasePathType;
  stage: FailureCaseStage;
  title: string;
  story: string;
  lessons: string[];
  regrets: string[];
  what_would_i_do: string;
}

/** 路径标签映射 */
export const PATH_LABELS: Record<FailureCasePathType, string> = {
  kaoyan: "考研",
  civil_service: "考公",
  employment: "求职",
  study_abroad: "留学",
};

/** 阶段标签映射 */
export const STAGE_LABELS: Record<FailureCaseStage, string> = {
  preparation: "备考阶段",
  interview: "面试/复试阶段",
  final_year1: "毕业第一年",
  year2_plus: "毕业两年+",
};

/** 路径徽章颜色映射 */
export const PATH_BADGE_COLORS: Record<
  FailureCasePathType,
  "blue" | "green" | "amber" | "purple"
> = {
  kaoyan: "blue",
  civil_service: "green",
  employment: "amber",
  study_abroad: "purple",
};
