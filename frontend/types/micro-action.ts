// 7天微行动相关类型定义
// 与后端 app/schemas/micro_action.py 对齐

export type MicroActionTargetPath =
  | "kaoyan"
  | "employment"
  | "civil_service"
  | string;

export type MicroActionTaskType =
  | "research"
  | "interview"
  | "practice"
  | "reflect";

export type MicroActionTaskStatus = "pending" | "completed" | "skipped";

export type MicroActionPlanStatus = "active" | "completed" | "abandoned";

/** 创建 7 天微行动计划请求体 */
export interface MicroActionPlanCreate {
  target_path: MicroActionTargetPath;
  target_role?: string | null;
}

/** 单日任务响应 */
export interface MicroActionTaskResponse {
  id: string;
  day_number: number;
  task_type: MicroActionTaskType;
  title: string;
  description: string;
  estimated_minutes: number;
  status: MicroActionTaskStatus;
  completed_at: string | null;
  user_response: string | null;
  insight: string | null;
}

/** 7 天微行动计划响应 */
export interface MicroActionPlanResponse {
  id: string;
  target_path: MicroActionTargetPath;
  target_role: string | null;
  status: MicroActionPlanStatus;
  started_at: string;
  completed_at: string | null;
  tasks: MicroActionTaskResponse[];
  progress: number;
  self_discovery_report: string | null;
}

/** 完成任务请求体 */
export interface TaskCompleteRequest {
  user_response: string;
}
