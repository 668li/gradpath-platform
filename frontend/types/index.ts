// 与后端 schema 对齐的类型定义

// ===== 认证 =====
export interface UserResponse {
  id: string;
  email: string;
  name: string;
  current_stage?: string | null;
  school?: string | null;
  major?: string | null;
  graduation_year?: number | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// ===== 去向决策 =====
export type DestinationType =
  | "employment"
  | "postgrad"
  | "civil_service"
  | "abroad"
  | "phd"
  | "startup"
  | "gap_year";

export type DecisionStatus = "planned" | "confirmed" | "executed" | "changed";

export interface DecisionDetails {
  [key: string]: string | undefined;
}

export interface DecisionResponse {
  id: string;
  user_id: string;
  decision_date: string;
  destination_type: DestinationType;
  status: DecisionStatus;
  details: DecisionDetails;
  reasoning: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
}

export interface DecisionCreate {
  decision_date: string;
  destination_type: DestinationType;
  status: DecisionStatus;
  details: DecisionDetails;
  reasoning?: string | null;
  confidence: number;
}

export interface DecisionUpdate {
  decision_date?: string;
  destination_type?: DestinationType;
  status?: DecisionStatus;
  details?: DecisionDetails;
  reasoning?: string | null;
  confidence?: number;
}

export type DecisionStats = Record<string, number>;

// ===== 职业事件 =====
export type EventType =
  | "onboard"
  | "leave"
  | "promotion"
  | "transfer"
  | "skill_acquired"
  | "project_done"
  | "certification"
  | "other";

export interface EventResponse {
  id: string;
  user_id: string;
  event_date: string;
  event_type: EventType;
  title: string;
  description: string | null;
  situation: string | null;
  task: string | null;
  action: string | null;
  result: string | null;
  reflection: string | null;
  skills_gained: string[];
  impact_metrics: Record<string, unknown> | null;
  mood: number | null;
  created_at: string;
  updated_at: string;
}

export interface EventCreate {
  event_date: string;
  event_type: EventType;
  title: string;
  description?: string | null;
  situation?: string | null;
  task?: string | null;
  action?: string | null;
  result?: string | null;
  reflection?: string | null;
  skills_gained?: string[];
  impact_metrics?: Record<string, unknown> | null;
  mood?: number | null;
}

export interface EventUpdate extends Partial<EventCreate> {}

// ===== 技能树 =====
export interface SkillResponse {
  id: string;
  user_id: string;
  name: string;
  category: string;
  level: number;
  parent_id: string | null;
  acquired_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  children: SkillResponse[];
}

export interface SkillCreate {
  name: string;
  category: string;
  level: number;
  parent_id?: string | null;
  acquired_date?: string | null;
  notes?: string | null;
}

export interface SkillUpdate extends Partial<SkillCreate> {}

export type SkillStats = Record<string, number>;

// ===== 阶段复盘 =====
export type PeriodType = "annual" | "quarterly" | "project" | "custom";

export interface RetrospectiveResponse {
  id: string;
  user_id: string;
  period_type: PeriodType;
  period_start: string;
  period_end: string;
  title: string;
  achievements: string[];
  challenges: string | null;
  lessons_learned: string | null;
  next_steps: string[];
  satisfaction: number;
  created_at: string;
  updated_at: string;
}

export interface RetroCreate {
  period_type: PeriodType;
  period_start: string;
  period_end: string;
  title: string;
  achievements?: string[];
  challenges?: string | null;
  lessons_learned?: string | null;
  next_steps?: string[];
  satisfaction: number;
}

export interface RetroUpdate extends Partial<RetroCreate> {}

export interface EventSummary {
  id: string;
  event_date: string;
  event_type: string;
  title: string;
}

export interface RetroDraft {
  period_start: string;
  period_end: string;
  event_summaries: EventSummary[];
  suggested_achievements: string[];
}

// ===== 看板 =====
export interface TimelineItem {
  id: string;
  date: string;
  type: "decision" | "event";
  title: string;
  subtitle?: string | null;
}

export interface DashboardOverview {
  decisions_count: number;
  events_count: number;
  skills_count: number;
  retrospectives_count: number;
  latest_decision: {
    id: string;
    destination_type: string;
    status: string;
    decision_date: string;
  } | null;
  recent_events: {
    id: string;
    title: string;
    event_type: string;
    event_date: string;
  }[];
  skill_categories: Record<string, number>;
  latest_retrospective: {
    id: string;
    title: string;
    period_end: string;
  } | null;
  timeline: TimelineItem[];
}
