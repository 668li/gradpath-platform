// 成长档案中心类型定义（对齐后端 app/schemas/growth.py）

/** 成长轨迹事件类型枚举 */
export type TrajectoryEventType =
  | "action_checkin"
  | "review_completed"
  | "milestone";

/** 档案状态枚举 */
export type ArchiveStatus = "ACTIVE" | "STALE";

/** 记录成长轨迹事件请求（user_id 由登录态 token 推断） */
export interface GrowthTrajectoryCreateRequest {
  event_type: TrajectoryEventType;
  /** 事件负载（打卡 / 复盘 / 里程碑明细） */
  event_payload: Record<string, unknown>;
  occurred_at: string;
  /** 上游事件幂等 ID（重复提交被丢弃） */
  source_event_id?: string | null;
}

/** 成长轨迹事件 VO */
export interface GrowthTrajectoryVO {
  id: number;
  user_id: string;
  event_type: TrajectoryEventType;
  event_payload: Record<string, unknown>;
  occurred_at: string;
  source_event_id: string | null;
}

/** 成长轨迹时间轴 VO */
export interface GrowthTrajectoryListResponse {
  items: GrowthTrajectoryVO[];
  total: number;
}

/** 档案聚合 VO */
export interface GrowthArchiveVO {
  user_id: string;
  /** 行动完成率；0.0~1.0，保留 2 位小数 */
  action_completion_rate: number;
  total_actions: number;
  completed_actions: number;
  /** 当前 Streak Days */
  streak_days: number;
  /** 加权行动完成分（D18 北极星指标） */
  weighted_action_score: number;
  archive_status: ArchiveStatus;
  /** 最近聚合时间 */
  updated_at: string;
}

/** 成长统计 VO（行动完成率 + Streak 统计） */
export interface GrowthStatsVO {
  user_id: string;
  /** 行动完成率；0.0~1.0 */
  action_completion_rate: number;
  current_streak_days: number;
  longest_streak_days: number;
  total_actions: number;
  completed_actions: number;
}
