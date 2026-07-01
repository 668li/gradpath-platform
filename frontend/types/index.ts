// 与后端 schema 对齐的类型定义

// ===== 通用分页响应 =====
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ===== 认证 =====
export interface UserResponse {
  id: string;
  email: string;
  name: string;
  current_stage?: string | null;
  school?: string | null;
  major?: string | null;
  graduation_year?: number | null;
  is_admin?: boolean;
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

// ===== 就业数据搜索 =====
export interface SchoolInfo {
  id: string;
  name: string;
  slug: string;
  code: string | null;
  report_count: number;
  major_count: number;
}

export interface EmploymentRecord {
  year: number;
  degree: string;
  total_graduates: number | null;
  rates: {
    employment: number | null;
    further_study: number | null;
    civil_service: number | null;
    abroad: number | null;
    startup: number | null;
    gap_year: number | null;
  };
  employer_ranking: { name: string; count: number }[];
  industry_distribution: Record<string, number>;
  destination_region: Record<string, number>;
  school_for_further_study: { name: string; count: number }[];
}

export interface EmploymentTrend {
  years: number[];
  employment_rate: (number | null)[];
  further_study_rate: (number | null)[];
  civil_service_rate: (number | null)[];
  abroad_rate: (number | null)[];
}

export interface EmploymentSearchResult {
  school: SchoolInfo | null;
  major: string | null;
  records: EmploymentRecord[];
  trend: EmploymentTrend | null;
}

export interface EmploymentStats {
  school_count: number;
  report_count: number;
  major_count: number;
  year_range: [number | null, number | null];
}

// ===== 社区数据 =====
export interface CommunityReport {
  id: string;
  school_name: string;
  major: string;
  graduation_year: number;
  degree: string;
  destination_type: string;
  employer: string | null;
  city: string | null;
  industry: string | null;
  salary_range: string | null;
}

export interface CommunitySubmit {
  school_name: string;
  major: string;
  graduation_year: number;
  degree: string;
  destination_type: string;
  employer?: string;
  city?: string;
  industry?: string;
  salary_range?: string;
}

export interface CommunityAggregate {
  school: string;
  major: string;
  sample_count: number;
  sufficient: boolean;
  destination_distribution: Record<string, number> | null;
  top_employers: { name: string; count: number }[] | null;
  top_cities: { name: string; count: number }[] | null;
  top_industries: { name: string; count: number }[] | null;
  salary_distribution: Record<string, number> | null;
}

export interface CommunityStats {
  total_reports: number;
  school_count: number;
  major_count: number;
}

// ===== 面试经验 =====
export interface InterviewReport {
  id: string;
  company: string;
  position: string;
  interview_year: number;
  city: string | null;
  rounds: number | null;
  result: string;
  dimensions: string[];
  difficulty: number | null;
  summary: string | null;
  community_report_id: string | null;
}

export interface InterviewSubmit {
  company: string;
  position: string;
  interview_year: number;
  city?: string;
  rounds?: number;
  result?: string;
  dimensions?: string[];
  difficulty?: number;
  summary?: string;
  community_report_id?: string;
}

export interface InterviewAggregate {
  company: string;
  position: string | null;
  sample_count: number;
  sufficient: boolean;
  avg_difficulty: number | null;
  avg_rounds: number | null;
  result_distribution: Record<string, number> | null;
  dimension_frequency: Record<string, number> | null;
  common_positions: { name: string; count: number }[] | null;
}

export interface InterviewStats {
  total_reports: number;
  company_count: number;
  position_count: number;
}

export interface CompanyInfo {
  name: string;
  count: number;
}

// ===== 数据管道 =====
export type ParseStatus = "pending" | "parsed" | "failed" | "reviewed" | "published";
export type SourceType = "crawl" | "upload" | "api";
export type ContentType = "html" | "pdf" | "excel" | "csv" | "json";

export interface ReportListItem {
  id: string;
  school_name: string;
  year: number;
  source_type: SourceType;
  content_type: ContentType | null;
  parse_status: ParseStatus;
  parse_error: string | null;
  parsed_at: string | null;
  created_at: string;
}

export interface ReportListResponse {
  items: ReportListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmploymentDataPreview {
  major: string;
  degree: string;
  total_graduates: number | null;
  employment_rate: number | null;
  further_study_rate: number | null;
}

export interface ReportDetail extends ReportListItem {
  source_url: string;
  employment_data: EmploymentDataPreview[];
}

export interface PipelineStats {
  total_reports: number;
  published_count: number;
  pending_count: number;
  failed_count: number;
}

export interface DataSourceResponse {
  id: string;
  name: string;
  source_type: string;
  api_url: string | null;
  api_key: string | null;
  data_mapping: Record<string, unknown> | null;
  is_active: boolean;
}

export interface DataSourceCreate {
  name: string;
  source_type?: string;
  api_url?: string | null;
  api_key?: string | null;
  data_mapping?: Record<string, unknown> | null;
  is_active?: boolean;
}

// ===== 讨论帖 =====
export type PostTopicType = "school_major" | "company_position";

export interface PostItem {
  id: string;
  topic_type: string;
  topic_key: string;
  content: string;
  author_id: string;
  author_name: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
  replies: PostItem[];
}

export interface PostListResponse {
  items: PostItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PostCreate {
  topic_type: string;
  topic_key: string;
  content: string;
  parent_id?: string | null;
}

// ===== AI 决策指导 =====
export interface DecisionAdviceRequest {
  destination_type: string;
  company?: string;
  position?: string;
  city?: string;
  expected_salary?: string;
}

export interface DecisionAlternative {
  option: string;
  reason: string;
}

export interface DecisionAdviceResponse {
  summary: string;
  pros: string[];
  cons: string[];
  market_analysis: string;
  alternatives: DecisionAlternative[];
  skill_gap: string[];
  confidence: number;
  advice: string;
}

// ===== 外部数据 =====
export interface Company {
  id: string;
  name: string;
  industry: string;
  size: string;
  stage: string | null;
  headquarters: string | null;
  description: string | null;
}

export interface SalaryBenchmark {
  id: string;
  company: string;
  position: string;
  city: string | null;
  experience_level: string;
  salary_min: number;
  salary_median: number;
  salary_max: number;
  source: string;
  year: number;
}

export interface MarketDataItem {
  id: string;
  indicator: string;
  category: string;
  value: number;
  unit: string;
  region: string | null;
  industry: string | null;
  year: number;
  source: string;
}

// ===== 游戏化 =====
export interface Badge {
  code: string;
  name: string;
  description: string;
  icon: string;
}

export interface ProgressInfo {
  current: number;
  needed: number;
  percent: number;
}

export interface GamificationProfile {
  xp: number;
  level: number;
  level_name: string;
  progress: ProgressInfo;
  earned_badges: Badge[];
  available_badges: Badge[];
  newly_awarded: Badge[];
}

export interface UserSetting {
  share_skills_enabled: boolean;
  share_token: string | null;
}

// ===== AI 成长洞察 =====
export interface GrowthInsightRequest {
  period_start: string;
  period_end: string;
}

export interface GrowthInsight {
  growth_score: number;
  trend: string;
  strengths: string[];
  gaps: string[];
  recommendations: string[];
  summary: string;
}

// ===== AI 复盘草稿 =====
export interface AIRetroDraftRequest {
  period_start: string;
  period_end: string;
}

export interface AIRetroDraft {
  achievements: string[];
  challenges: string;
  lessons_learned: string;
  next_steps: string[];
  suggested_satisfaction: number;
  summary: string;
}

// ===== 分享 =====
export interface ShareableSkills {
  user_name: string;
  skills: {
    id: string;
    name: string;
    category: string;
    level: number;
    parent_id: string | null;
    acquired_date: string | null;
    notes: string | null;
  }[];
}

// ===== AI 职业管家 — 对话 =====
export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  active_skills: string[];
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  skill_used: string | null;
  context_snapshot: Record<string, unknown>;
  created_at: string;
}

export interface SendMessageRequest {
  content: string;
  skill_hint?: string | null;
}

export interface SendMessageResponse {
  content: string;
  skill_used: string;
  career_plan: string | null;
}

export interface SkillInfo {
  code: string;
  name: string;
  description: string;
  icon: string;
}

// ===== AI 职业管家 — 职业规划 =====
export interface Milestone {
  title: string;
  description?: string;
  status: string;
  target_date?: string;
}

export interface CareerPlan {
  id: string;
  user_id: string;
  conversation_id: string | null;
  goal_text: string;
  current_state: Record<string, unknown>;
  target_state: Record<string, unknown>;
  gaps: string[];
  milestones: Milestone[];
  timeline_months: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface MilestoneLog {
  id: string;
  plan_id: string;
  milestone_index: number;
  content: string;
  created_at: string;
}

export interface ReminderItem {
  plan_id: string;
  plan_goal: string;
  milestone_title: string;
  milestone_index: number;
  target_date: string | null;
  days_remaining: number | null;
  type: "overdue" | "upcoming";
}

// ===== 职业测评 =====
export interface QuestionOption {
  value: string;
  label: string;
}

export interface AssessmentQuestion {
  id: string;
  question: string;
  options: QuestionOption[];
}

export interface AssessmentResult {
  id: string;
  assessment_type: string;
  result_code: string;
  result_summary: string;
  recommended_directions: string[];
  scores: Record<string, number>;
  created_at: string;
}

// ===== 每日重点 =====
export interface DailyFocusItem {
  plan_id: string;
  plan_goal: string;
  milestone_title: string;
  milestone_index: number;
  milestone_description: string | null;
  status: string;
  has_logs: boolean;
}

// ===== 周回顾 =====
export interface WeeklyRecap {
  completed_this_week: number;
  logs_this_week: number;
  upcoming_deadlines: ReminderItem[];
  active_plans: number;
  total_milestones_done: number;
  total_milestones: number;
  encouragement: string;
}

// ===== 用户职业画像 =====
export interface CareerProfile {
  id: string;
  user_id: string;
  education_level: string | null;
  major: string | null;
  school_name: string | null;
  school_tier: string | null;
  graduation_year: number | null;
  target_direction: string | null;
  target_industry: string | null;
  technical_skill: number;
  communication_skill: number;
  leadership_skill: number;
  creativity_skill: number;
  self_introduction: string | null;
  created_at: string;
  updated_at: string;
}

export interface CareerProfileCreate {
  education_level?: string | null;
  major?: string | null;
  school_name?: string | null;
  school_tier?: string | null;
  graduation_year?: number | null;
  target_direction?: string | null;
  target_industry?: string | null;
  technical_skill?: number;
  communication_skill?: number;
  leadership_skill?: number;
  creativity_skill?: number;
  self_introduction?: string | null;
}

// ===== 规划模板 =====
export interface PlanTemplate {
  id: string;
  name: string;
  icon: string;
  description: string;
  goal_text: string;
  timeline_months: number;
  milestones: Milestone[];
}

// ===== 知识库 =====
export interface KnowledgeArticle {
  id: string;
  category: string;
  title: string;
  content: string;
  tags: string[];
  source: string | null;
  metadata_: Record<string, unknown>;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeArticleCreate {
  category: string;
  title: string;
  content: string;
  tags?: string[];
  source?: string | null;
  metadata_?: Record<string, unknown>;
  is_published?: boolean;
}

export interface KnowledgeArticleUpdate {
  category?: string;
  title?: string;
  content?: string;
  tags?: string[];
  source?: string | null;
  metadata_?: Record<string, unknown>;
  is_published?: boolean;
}
