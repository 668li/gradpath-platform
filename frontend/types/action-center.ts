// 行动任务中心类型定义（对齐后端 app/schemas/action.py）
// 契约枚举按后端以 str + 注释形式声明

/** 行动类型枚举 */
export type ActionType =
  | "read_article"
  | "finish_course"
  | "resume_revise"
  | "mock_interview"
  | "real_apply"
  | "get_offer"
  | "custom";

/** 行动状态枚举 */
export type ActionStatus = "PENDING" | "DONE" | "EXPIRED" | "CANCELED";

/** 连击状态枚举 */
export type StreakStatus = "ACTIVE" | "BROKEN" | "NEVER";

/** 创建行动项请求（user_id 由登录态 token 推断） */
export interface ActionCreateRequest {
  action_type: ActionType;
  title: string;
  /** 计划完成日期；格式 年-月-日（如 2026-01-15） */
  due_date: string;
  /** 来源决策分析 ID（决策中心联动） */
  source_decision_id?: number | null;
  /** 备注（契约字段，当前创建时忽略） */
  note?: string | null;
  /** 业务方扩展（契约字段，当前创建时忽略） */
  biz_fields?: Record<string, unknown>;
}

/** 更新行动项请求（部分更新，均可选） */
export interface ActionUpdateRequest {
  title?: string | null;
  due_date?: string | null;
  status?: ActionStatus | null;
  note?: string | null;
}

/** 行动打卡请求 */
export interface CheckinRequest {
  action_id: number;
  /** 打卡时间 ISO 字符串 */
  completed_at: string;
  evidence_url?: string | null;
  note?: string | null;
}

/** 连续天数统计 VO */
export interface StreakVO {
  user_id: string;
  current_streak_days: number;
  longest_streak_days: number;
  last_checkin_date: string | null;
  streak_status: StreakStatus;
}

/** 行动项 VO */
export interface ActionVO {
  id: number;
  user_id: string;
  action_type: ActionType;
  title: string;
  due_date: string;
  source_decision_id: number | null;
  weight: number;
  status: ActionStatus;
  created_time: string;
}

/** 行动列表 VO */
export interface ActionListResponse {
  items: ActionVO[];
  total: number;
}

/** 打卡记录 VO */
export interface CheckinVO {
  id: number;
  action_id: number;
  user_id: string;
  completed_at: string;
  evidence_url: string | null;
  note: string | null;
  biz_req_no: string;
}

/** 打卡历史列表 VO */
export interface CheckinListResponse {
  items: CheckinVO[];
  total: number;
}

/** 行动权重 VO */
export interface ActionWeightVO {
  id: number;
  action_type: ActionType;
  weight: number;
  weight_label: string;
  enabled: boolean;
}

/** 行动权重列表 VO */
export interface ActionWeightListResponse {
  items: ActionWeightVO[];
  total: number;
}
