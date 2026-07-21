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
  agree_terms?: boolean;
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
  // 决策日志字段
  prediction?: string | null;
  assumptions?: string[];
  review_date?: string | null;
  actual_outcome?: string | null;
  review_notes?: string | null;
  review_completed?: boolean;
  ai_analysis?: string | null;
}

export interface DecisionCreate {
  decision_date: string;
  destination_type: DestinationType;
  status: DecisionStatus;
  details: DecisionDetails;
  reasoning?: string | null;
  confidence: number;
  prediction?: string | null;
  assumptions?: string[];
  review_date?: string | null;
}

export interface DecisionUpdate {
  decision_date?: string;
  destination_type?: DestinationType;
  status?: DecisionStatus;
  details?: DecisionDetails;
  reasoning?: string | null;
  confidence?: number;
  prediction?: string | null;
  assumptions?: string[];
  review_date?: string | null;
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
  title?: string | null;
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

// 修复: 此处原为 `interface SkillInfo`, 与 L1805 处 "Skill 管理" 模块的 SkillInfo 同名,
// TypeScript 会自动合并两者, 导致合并后的类型要求所有字段都必填,
// 但 chat 接口 (/api/chat/skills) 与 skill-toolbox 接口 (/api/skill-toolbox) 返回字段完全不同。
// 因此将聊天用的 Skill 重命名为 ChatSkillInfo, 与 L1805 的 SkillInfo 区分开。
export interface ChatSkillInfo {
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
// 测评类型
export type AssessmentType = "holland" | "mbti" | "big_five" | "disc";

// 测评选项
export interface QuestionOption {
  value: string;
  label: string;
}

// 题目
export interface Question {
  id: string;
  question: string;
  options: QuestionOption[];
}

// 测评提交
export interface AssessmentSubmit {
  assessment_type: AssessmentType;
  answers: Record<string, string>;
}

// 测评响应
export interface AssessmentResponse {
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

// ===== 护城河功能：人生平衡轮 =====
export interface LifeWheelDimension {
  key: string;
  name: string;
  desc: string;
}

export interface LifeWheelSnapshot {
  id: string;
  snapshot_date: string;
  scores: Record<string, number>;
  overall_score: number;
  ai_analysis: string | null;
  notes: string | null;
  created_at: string;
}

export interface LifeWheelSubmit {
  scores: Record<string, number>;
  notes?: string | null;
}

// ===== 护城河功能：连续打卡 =====
export interface StreakRecord {
  date: string;
  streak_count: number;
  activity_types: string[];
  xp_earned: number;
  is_rest_day: boolean;
  is_redeem: boolean;
  action_type: string | null;
  action_detail: string | null;
}

export interface StreakMilestone {
  days: number;
  name: string;
  unlocked: boolean;
}

export interface StreakStats {
  current_streak: number;
  longest_streak: number;
  total_active_days: number;
  today_active: boolean;
  last_active_date: string | null;
  freeze_available: boolean;
  recent_records: StreakRecord[];
  milestones: StreakMilestone[];
  rest_day_available: boolean;
  redeem_available: boolean;
}

export interface StreakCheckInRequest {
  action_type: "main" | "micro";
  action_detail: string;
}

export interface StreakCheckInResponse {
  streak_count: number;
  activity_types: string[];
  xp_earned: number;
  is_new_record: boolean;
}

// ===== 护城河功能：AI 主动洞察 =====
export interface ProactiveInsight {
  id: string;
  insight_type: "pattern" | "reminder" | "celebration" | "warning" | "suggestion";
  title: string;
  content: string;
  action_suggestion: string | null;
  priority: number;
  related_data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface ProactiveInsightSummary {
  unread_count: number;
  total_count: number;
  latest_insights: ProactiveInsight[];
}

// ===== 护城河功能：人生设计引擎 =====
export interface AuditQuestion {
  question: string;
  answer: string;
}

export interface SprintGoal {
  title: string;
  measurable_result: string;
  deadline?: string | null;
}

export interface SprintCreate {
  name: string;
  primary_domain: string;
  maintenance_domains: string[];
  start_date: string;
  end_date: string;
  goals: SprintGoal[];
  vision_statement?: string | null;
  audit_summary?: string | null;
  audit_qa: AuditQuestion[];
}

export interface SprintResponse {
  id: string;
  name: string;
  primary_domain: string;
  maintenance_domains: string[];
  start_date: string;
  end_date: string;
  status: string;
  goals: SprintGoal[];
  vision_statement: string | null;
  audit_summary: string | null;
  audit_qa: AuditQuestion[];
  review_notes: string | null;
  ai_review: string | null;
  created_at: string;
}

export interface WeeklyReviewCreate {
  sprint_id?: string | null;
  week_start: string;
  week_end: string;
  planned_actions?: string | null;
  actual_actions?: string | null;
  what_worked?: string | null;
  what_didnt_work?: string | null;
  next_week_plan?: string | null;
  energy_level?: number | null;
}

export interface WeeklyReviewResponse {
  id: string;
  sprint_id: string | null;
  week_start: string;
  week_end: string;
  planned_actions: string | null;
  actual_actions: string | null;
  what_worked: string | null;
  what_didnt_work: string | null;
  next_week_plan: string | null;
  energy_level: number | null;
  ai_analysis: string | null;
  created_at: string;
}

// ===== 护城河功能：决策深度分析 =====
export interface Criterion {
  criterion: string;
  weight: number;
}

export interface MatrixOption {
  name: string;
  scores: Record<string, number>;
}

export interface PremortemReason {
  reason: string;
  category: string;
}

export interface Safeguard {
  category: string;
  action: string;
}

export interface DecisionAnalysisCreate {
  title: string;
  decision_id?: string | null;
  options: string[];
  premortem_reasons: PremortemReason[];
  premortem_categories: string[];
  safeguards: Safeguard[];
  criteria: Criterion[];
  matrix_scores: Record<string, unknown>[];
  red_team_questions: string[];
  red_team_answers: string[];
}

export interface DecisionAnalysisResponse {
  id: string;
  decision_id: string | null;
  title: string;
  options: string[];
  premortem_reasons: PremortemReason[];
  premortem_categories: string[];
  safeguards: Safeguard[];
  criteria: Criterion[];
  matrix_scores: Record<string, unknown>[];
  weighted_results: { name: string; total: number; details: Record<string, number> }[];
  winner: string | null;
  red_team_questions: string[];
  red_team_answers: string[];
  ai_analysis: string | null;
  recommendation: string | null;
  created_at: string;
}

export interface MatrixComputeRequest {
  criteria: Criterion[];
  matrix_scores: MatrixOption[];
}

export interface PremortemAnalyzeRequest {
  title: string;
  options: string[];
  premortem_reasons: string[];
}

export interface RedTeamGenerateRequest {
  title: string;
  options: string[];
  reasoning?: string | null;
}

// ===== 护城河功能：AI 导师人格库 =====
export interface MentorPersona {
  code: string;
  name: string;
  icon: string;
  tagline: string;
}

export interface MentorAdviceRequest {
  persona_code: string;
  question: string;
  user_context?: string;
}

export interface MultiPerspectiveRequest {
  persona_codes: string[];
  question: string;
  user_context?: string;
}

export interface MentorPerspectiveResult {
  persona_code: string;
  persona_name: string;
  persona_icon: string;
  advice: string;
}

export interface MultiPerspectiveResponse {
  perspectives: MentorPerspectiveResult[];
}

// ===== 护城河功能：成长模式智能 =====
export interface GrowthPattern {
  pattern_type: string;
  title: string;
  description: string;
  data_points: Record<string, unknown>;
  suggestion: string;
}

export interface GrowthPatternResponse {
  patterns: GrowthPattern[];
  calibration_score: number;
  total_data_points: number;
}

// ===== 考研作战室：院校情报 =====
export type DiscriminationLevel = "none" | "mild" | "moderate" | "severe" | "unknown";
export type ProtectionLevel = "yes" | "no" | "partial" | "unknown";
export type SuppressionLevel = "none" | "mild" | "moderate" | "severe" | "unknown";
export type TransferLevel = "friendly" | "neutral" | "unfriendly" | "unknown";

export interface IntelQueryRequest {
  school_name: string;
  major_name: string;
}

export interface AIIntelResult {
  school_name: string;
  major_name: string;
  school_tier: string;
  background_discrimination: DiscriminationLevel;
  first_choice_protection: ProtectionLevel;
  admission_ratio: string | null;
  push_ratio: string | null;
  actual_quota: number | null;
  score_line: number | null;
  retest_weight: string | null;
  retest_format: string | null;
  score_suppression: SuppressionLevel;
  transfer_friendly: TransferLevel;
  insider_notes: string | null;
  data_sources: string[];
  tags: string[];
  ai_summary: string;
}

export interface IntelSaveRequest {
  school_name: string;
  major_name: string;
  school_tier?: string;
  year?: number;
  background_discrimination?: DiscriminationLevel;
  first_choice_protection?: ProtectionLevel;
  admission_ratio?: string | null;
  push_ratio?: string | null;
  actual_quota?: number | null;
  score_line?: number | null;
  retest_weight?: string | null;
  retest_format?: string | null;
  score_suppression?: SuppressionLevel;
  transfer_friendly?: TransferLevel;
  insider_notes?: string | null;
  data_sources?: string[];
  tags?: string[];
  ai_summary?: string | null;
  is_ai_generated?: boolean;
}

export interface IntelResponse {
  id: string;
  school_name: string;
  major_name: string;
  school_tier: string;
  year: number;
  background_discrimination: DiscriminationLevel;
  first_choice_protection: ProtectionLevel;
  admission_ratio: string | null;
  push_ratio: string | null;
  actual_quota: number | null;
  score_line: number | null;
  retest_weight: string | null;
  retest_format: string | null;
  score_suppression: SuppressionLevel;
  transfer_friendly: TransferLevel;
  insider_notes: string | null;
  data_sources: string[];
  tags: string[];
  ai_summary: string | null;
  is_ai_generated: boolean;
  created_at: string;
}

// ===== 考研作战室：自我定位 =====
export interface PositioningCreateRequest {
  undergrad_tier: string;
  undergrad_major?: string | null;
  gpa?: number | null;
  gpa_rank?: string | null;
  english_level?: string | null;
  english_score?: number | null;
  research_experience?: string | null;
  competitions?: string[];
  awards?: string | null;
  internships?: string | null;
  target_school?: string | null;
  target_major?: string | null;
  target_region?: string | null;
  other_info?: string | null;
}

export interface SchoolRecommendation {
  name: string;
  major: string;
  tier: string;
  reason: string;
  probability: number;
}

export interface PositioningResponse {
  id: string;
  undergrad_tier: string;
  undergrad_major: string | null;
  gpa: number | null;
  gpa_rank: string | null;
  english_level: string | null;
  english_score: number | null;
  research_experience: string | null;
  competitions: string[];
  awards: string | null;
  internships: string | null;
  target_school: string | null;
  target_major: string | null;
  target_region: string | null;
  other_info: string | null;
  ai_assessment: string | null;
  reach_schools: SchoolRecommendation[];
  target_schools: SchoolRecommendation[];
  safety_schools: SchoolRecommendation[];
  success_probability: number | null;
  risk_warnings: string[];
  created_at: string;
}

// ===== 考研作战室：暗知识 =====
export interface DarkKnowledgeResponse {
  id: string;
  stage: string;
  category: string;
  title: string;
  content: string;
  importance: "critical" | "high" | "medium";
  common_misconception: string | null;
  actionable_advice: string | null;
  verification_method: string | null;
  tags: string[];
  sort_order: number;
}

export interface DarkKnowledgeStage {
  stage: string;
  stage_name: string;
  count: number;
}

// ===== 考研作战室：研招网真实数据 =====
export interface GradYanzhaoProgram {
  id: string;
  university_name: string;
  department: string;
  major_name: string;
  degree_type: string;
  research_directions: string[];
  enrollment_quota: number | null;
  tuition: string | null;
  duration: string | null;
  study_mode: string | null;
  admission_requirements: string | null;
  contact_info: string | null;
  source_url: string | null;
  year: number;
  data_sources: string[];
  created_at: string;
  updated_at: string;
}

export interface GradScorelineRecord {
  id: string;
  university_name: string;
  major_name: string;
  degree_type: string | null;
  year: number;
  total_score_line: number | null;
  politics_score: number | null;
  foreign_language_score: number | null;
  business_1_score: number | null;
  business_2_score: number | null;
  enrollment_count: number | null;
  application_count: number | null;
  adjustment_count: number | null;
  data_sources: string[];
  created_at: string;
  updated_at: string;
}

export interface GradScorelineTrend {
  university_name: string;
  major_name: string;
  degree_type: string | null;
  years: number[];
  total_score_lines: (number | null)[];
  politics_scores: (number | null)[];
  foreign_language_scores: (number | null)[];
  business_1_scores: (number | null)[];
  business_2_scores: (number | null)[];
  application_counts: (number | null)[];
  enrollment_counts: (number | null)[];
}

export interface GradAdjustmentInfo {
  id: string;
  university_name: string;
  department: string;
  major_name: string;
  degree_type: string | null;
  original_major_range: string | null;
  adjustment_quota: number | null;
  contact_email: string | null;
  contact_phone: string | null;
  deadline: string | null;
  source_url: string | null;
  year: number;
  status: string;
  data_sources: string[];
  created_at: string;
  updated_at: string;
}

export interface GradSchoolDataSummary {
  university_name: string;
  program_count: number;
  latest_year: number | null;
  latest_scoreline: number | null;
  scoreline_trend: "up" | "down" | "stable";
  has_adjustment: boolean;
  adjustment_count: number;
}

// ===== AI 推荐系统 =====
export interface SchoolRecommendation {
  name: string;
  province: string;
  level: string;
  match_score: number;
  match_reasons: string[];
  score_line: number | null;
  adjustment_available: boolean;
}

export interface AdjustmentRecommendation {
  university_name: string;
  department: string;
  major_name: string;
  match_score: number;
  match_reasons: string[];
  adjustment_quota: number | null;
  deadline: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  source_url: string | null;
}

export interface DarkKnowledgeRecommendation {
  id: string;
  stage: string;
  category: string;
  title: string;
  content: string;
  importance: string;
  common_misconception: string | null;
  actionable_advice: string | null;
  relevance_score: number;
}

export interface RecommendationResponse<T> {
  items: T[];
  total: number;
}

// ===== 求职作战室：公司情报 =====
export type OvertimeLevel = "none" | "mild" | "moderate" | "severe" | "unknown";
export type LayoffLevel = "none" | "low" | "moderate" | "high" | "unknown";
export type PromotionLevel = "good" | "fair" | "poor" | "unknown";
export type EducationBarrierLevel = "none" | "mild" | "moderate" | "severe" | "unknown";
export type SalaryHonestyLevel = "honest" | "exaggerated" | "misleading" | "unknown";
export type CultureLevel = "good" | "neutral" | "toxic" | "unknown";

export interface CompanyIntelQueryRequest {
  company_name: string;
  position_name: string;
}

export interface AICompanyIntelResult {
  company_name: string;
  position_name: string;
  industry: string;
  overtime_intensity: OvertimeLevel;
  layoff_risk: LayoffLevel;
  promotion_outlook: PromotionLevel;
  education_barrier: EducationBarrierLevel;
  salary_honesty: SalaryHonestyLevel;
  culture_fit: CultureLevel;
  salary_range: string | null;
  actual_salary: string | null;
  interview_style: string | null;
  interview_rounds: number | null;
  turnover_rate: string | null;
  growth_path: string | null;
  insider_notes: string | null;
  risk_warnings: string[];
  data_sources: string[];
  tags: string[];
  ai_summary: string;
}

export interface CompanyIntelSaveRequest {
  company_name: string;
  position_name: string;
  industry?: string;
  overtime_intensity?: OvertimeLevel;
  layoff_risk?: LayoffLevel;
  promotion_outlook?: PromotionLevel;
  education_barrier?: EducationBarrierLevel;
  salary_honesty?: SalaryHonestyLevel;
  culture_fit?: CultureLevel;
  salary_range?: string | null;
  actual_salary?: string | null;
  interview_style?: string | null;
  interview_rounds?: number | null;
  turnover_rate?: string | null;
  growth_path?: string | null;
  insider_notes?: string | null;
  risk_warnings?: string[];
  data_sources?: string[];
  tags?: string[];
  ai_summary?: string | null;
  is_ai_generated?: boolean;
}

export interface CompanyIntelResponse {
  id: string;
  company_name: string;
  position_name: string;
  industry: string;
  overtime_intensity: OvertimeLevel;
  layoff_risk: LayoffLevel;
  promotion_outlook: PromotionLevel;
  education_barrier: EducationBarrierLevel;
  salary_honesty: SalaryHonestyLevel;
  culture_fit: CultureLevel;
  salary_range: string | null;
  actual_salary: string | null;
  interview_style: string | null;
  interview_rounds: number | null;
  turnover_rate: string | null;
  growth_path: string | null;
  insider_notes: string | null;
  risk_warnings: string[];
  data_sources: string[];
  tags: string[];
  ai_summary: string | null;
  is_ai_generated: boolean;
  created_at: string;
}

// ===== 求职作战室：求职定位 =====
export interface CareerPositioningCreateRequest {
  education_level: string;
  school_tier?: string;
  major?: string | null;
  graduation_year?: number | null;
  gpa?: number | null;
  internships?: string | null;
  skills?: string[];
  competitions?: string[];
  projects?: string | null;
  certifications?: string | null;
  target_industry?: string | null;
  target_position?: string | null;
  target_city?: string | null;
  salary_expectation?: string | null;
  other_info?: string | null;
}

export interface CompanyRecommendation {
  name: string;
  position: string;
  tier: string;
  reason: string;
  probability: number;
}

export interface SkillGap {
  skill: string;
  importance: string;
  suggestion: string;
}

export interface CareerPositioningResponse {
  id: string;
  education_level: string;
  school_tier: string;
  major: string | null;
  graduation_year: number | null;
  gpa: number | null;
  internships: string | null;
  skills: string[];
  competitions: string[];
  projects: string | null;
  certifications: string | null;
  target_industry: string | null;
  target_position: string | null;
  target_city: string | null;
  salary_expectation: string | null;
  other_info: string | null;
  ai_assessment: string | null;
  competitiveness_score: number | null;
  reach_companies: CompanyRecommendation[];
  target_companies: CompanyRecommendation[];
  safety_companies: CompanyRecommendation[];
  salary_estimate: string | null;
  skill_gaps: SkillGap[];
  risk_warnings: string[];
  created_at: string;
}

// ===== 求职作战室：求职暗知识 =====
export interface CareerDarkKnowledgeResponse {
  id: string;
  stage: string;
  category: string;
  title: string;
  content: string;
  importance: "critical" | "high" | "medium";
  common_misconception: string | null;
  actionable_advice: string | null;
  verification_method: string | null;
  tags: string[];
  sort_order: number;
}

export interface CareerDarkKnowledgeStage {
  stage: string;
  stage_name: string;
  count: number;
}

// ===== 考公作战室：岗位情报 =====
export type RealCompetitionLevel = "low" | "medium" | "high" | "extreme" | "unknown";
export type TreatmentLevel = "low" | "medium" | "high" | "top" | "unknown";
export type PromotionSpeedLevel = "slow" | "medium" | "fast" | "unknown";
export type WorkloadLevel = "light" | "moderate" | "heavy" | "extreme" | "unknown";
export type RadishPostLevel = "unlikely" | "possible" | "likely" | "unknown";
export type ServicePeriodLevel = "yes" | "no" | "unknown";

export interface PostIntelQueryRequest {
  region: string;
  department: string;
  post_name: string;
  exam_type?: string;
}

export interface AIPostIntelResult {
  region: string;
  department: string;
  post_name: string;
  exam_type: string;
  real_competition: RealCompetitionLevel;
  treatment_level: TreatmentLevel;
  promotion_speed: PromotionSpeedLevel;
  workload: WorkloadLevel;
  radish_post: RadishPostLevel;
  service_period: ServicePeriodLevel;
  admission_ratio: string | null;
  cutoff_score: number | null;
  salary_estimate: string | null;
  housing_fund: string | null;
  bonus_info: string | null;
  department_tier: string | null;
  work_content: string | null;
  insider_notes: string | null;
  risk_warnings: string[];
  data_sources: string[];
  tags: string[];
  ai_summary: string;
}

export interface PostIntelSaveRequest {
  region: string;
  department: string;
  post_name: string;
  exam_type?: string;
  real_competition?: RealCompetitionLevel;
  treatment_level?: TreatmentLevel;
  promotion_speed?: PromotionSpeedLevel;
  workload?: WorkloadLevel;
  radish_post?: RadishPostLevel;
  service_period?: ServicePeriodLevel;
  admission_ratio?: string | null;
  cutoff_score?: number | null;
  salary_estimate?: string | null;
  housing_fund?: string | null;
  bonus_info?: string | null;
  department_tier?: string | null;
  work_content?: string | null;
  insider_notes?: string | null;
  risk_warnings?: string[];
  data_sources?: string[];
  tags?: string[];
  ai_summary?: string | null;
  is_ai_generated?: boolean;
}

export interface PostIntelResponse {
  id: string;
  region: string;
  department: string;
  post_name: string;
  exam_type: string;
  real_competition: RealCompetitionLevel;
  treatment_level: TreatmentLevel;
  promotion_speed: PromotionSpeedLevel;
  workload: WorkloadLevel;
  radish_post: RadishPostLevel;
  service_period: ServicePeriodLevel;
  admission_ratio: string | null;
  cutoff_score: number | null;
  salary_estimate: string | null;
  housing_fund: string | null;
  bonus_info: string | null;
  department_tier: string | null;
  work_content: string | null;
  insider_notes: string | null;
  risk_warnings: string[];
  data_sources: string[];
  tags: string[];
  ai_summary: string | null;
  is_ai_generated: boolean;
  created_at: string;
}

// ===== 考公作战室：考公定位 =====
export interface CivilServicePositioningCreateRequest {
  education_level: string;
  school_tier?: string;
  major?: string | null;
  is_party_member?: boolean;
  student_leader?: boolean;
  has_honors?: boolean;
  is_fresh_graduate?: boolean;
  target_region?: string | null;
  target_type?: string | null;
  family_background?: string | null;
  other_info?: string | null;
}

export interface CivilServicePostRecommendation {
  region: string;
  department: string;
  post: string;
  reason: string;
  probability: number;
}

export interface CivilServicePositioningResponse {
  id: string;
  education_level: string;
  school_tier: string;
  major: string | null;
  is_party_member: boolean;
  student_leader: boolean;
  has_honors: boolean;
  is_fresh_graduate: boolean;
  target_region: string | null;
  target_type: string | null;
  family_background: string | null;
  other_info: string | null;
  ai_assessment: string | null;
  competitiveness_score: number | null;
  eligible_for_xuandiao: boolean;
  reach_posts: CivilServicePostRecommendation[];
  target_posts: CivilServicePostRecommendation[];
  safety_posts: CivilServicePostRecommendation[];
  preparation_timeline: string | null;
  risk_warnings: string[];
  created_at: string;
}

// ===== 考公作战室：考公暗知识 =====
export interface CivilServiceDarkKnowledgeResponse {
  id: string;
  stage: string;
  category: string;
  title: string;
  content: string;
  importance: "critical" | "high" | "medium" | "low";
  common_misconception: string | null;
  actionable_advice: string | null;
  verification_method: string | null;
  tags: string[];
  sort_order: number;
}

export interface CivilServiceDarkKnowledgeStage {
  stage: string;
  stage_name: string;
  count: number;
}

// ===== 爬虫管理后台 =====
export type CrawlerCategory = "grad" | "civil" | "career" | "reports";
export type CrawlerLastStatus = "success" | "failed" | "running" | null;
export type CrawlerRunStatus = "success" | "failed" | "running";

export interface CrawlerInfo {
  name: string;
  category: CrawlerCategory;
  description: string;
  last_run_at: string | null;
  last_status: CrawlerLastStatus;
  last_items_stored: number | null;
}

export interface CrawlerRun {
  id: string;
  source_name: string;
  category: string;
  status: CrawlerRunStatus;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  items_fetched: number;
  items_stored: number;
  items_duplicates: number;
  error_count: number;
  error_message: string | null;
  log: string;
}

// ===== 考研导师评价系统 =====
export interface MentorResponse {
  id: string;
  name: string;
  university: string;
  department: string;
  title: string;
  research_directions: string[];
  paper_count: number;
  project_count: number;
  citation_count: number;
  h_index: number | null;
  academic_homepage: string | null;
  google_scholar_url: string | null;
  cnki_url: string | null;
  enrollment_status: string;
  enrollment_directions: string[];
  contact_email: string | null;
  contact_phone: string | null;
  avg_rating: number;
  review_count: number;
  rating_academic: number;
  rating_guidance: number;
  rating_relationship: number;
  rating_funding: number;
  rating_workload: number;
  rating_career: number;
  source_url: string | null;
  source_platform: string;
  is_verified: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface MentorListResponse {
  items: MentorResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface MentorReviewResponse {
  id: string;
  mentor_id: string;
  user_id: string;
  is_anonymous: boolean;
  anonymous_id: string | null;
  rating_academic: number;
  rating_guidance: number;
  rating_relationship: number;
  rating_funding: number;
  rating_workload: number;
  rating_career: number;
  overall_rating: number;
  title: string;
  content: string;
  pros: string[];
  cons: string[];
  review_status: string;
  like_count: number;
  is_helpful: boolean;
  submitted_at: string;
  is_verified: boolean;
  verification_proof: string | null;
  reviewer_identity: string | null;
  created_at: string;
  updated_at: string;
}

export interface MentorReviewListResponse {
  items: MentorReviewResponse[];
  total: number;
  page: number;
  page_size: number;
}

// ===== Skill 管理 =====
export type SkillCategory = "builder" | "advisor" | "generator";

export interface SkillInfo {
  name: string;
  display_name: string;
  description: string;
  trigger_words: string[];
  use_cases: string[];
  capabilities: string[];
  limitations: string[];
  category: SkillCategory;
  is_active: boolean;
}

export interface SkillListResponse {
  items: SkillInfo[];
  total: number;
}

export interface MentorReviewCreate {
  is_anonymous?: boolean;
  anonymous_id?: string;
  rating_academic: number;
  rating_guidance: number;
  rating_relationship: number;
  rating_funding: number;
  rating_workload: number;
  rating_career: number;
  title: string;
  content: string;
  pros?: string[];
  cons?: string[];
  reviewer_identity?: string;
}

// ===== 考研社区交流系统 =====
export interface ExperiencePostResponse {
  id: string;
  user_id: string;
  title: string;
  summary: string | null;
  content: string;
  tags: string[];
  category: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  is_pinned: boolean;
  is_anonymous: boolean;
  status: string;
  source_platform: string;
  source_url: string | null;
  external_view_count: number;
  external_like_count: number;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExperiencePostCreate {
  title: string;
  summary?: string | null;
  content: string;
  tags?: string[];
  category?: string;
  is_anonymous?: boolean;
  source_platform?: string;
  source_url?: string | null;
}

export interface ExperiencePostUpdate {
  title?: string;
  summary?: string | null;
  content?: string;
  tags?: string[];
  category?: string;
  is_anonymous?: boolean;
  source_url?: string | null;
}

export interface QAAnswerResponse {
  id: string;
  qa_id: string;
  user_id: string;
  content: string;
  is_best: boolean;
  like_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface QAAnswerCreate {
  content: string;
}

export interface QAResponse {
  id: string;
  user_id: string;
  title: string;
  content: string;
  tags: string[];
  status: string;
  view_count: number;
  answer_count: number;
  is_resolved: boolean;
  best_answer_id: string | null;
  answers: QAAnswerResponse[];
  created_at: string;
  updated_at: string;
}

export interface QACreate {
  title: string;
  content: string;
  tags?: string[];
}

export interface QAUpdate {
  title?: string;
  content?: string;
  tags?: string[];
}

// ===== 学习计划 =====
export interface StudyPlan {
  id: string;
  user_id: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  subjects: string[] | null;
  completed: boolean;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface StudyPlanCreate {
  title: string;
  start_date?: string | null;
  end_date?: string | null;
  subjects?: string[] | null;
  completed?: boolean;
  progress?: number;
}

export interface StudyPlanUpdate {
  title?: string;
  start_date?: string | null;
  end_date?: string | null;
  subjects?: string[] | null;
  completed?: boolean;
  progress?: number;
}

// ===== 学习资源 =====
export interface LearningResource {
  id: string;
  user_id: string;
  title: string;
  url: string | null;
  resource_type: string;
  subject: string;
  difficulty: string;
  description: string | null;
  tags: string[] | null;
  rating: number;
  is_free: boolean;
  view_count: number;
  created_at: string;
  updated_at: string;
}

export interface LearningResourceCreate {
  title: string;
  url?: string | null;
  resource_type: string;
  subject: string;
  difficulty: string;
  description?: string | null;
  tags?: string[] | null;
  rating?: number;
  is_free?: boolean;
}

export interface LearningResourceUpdate {
  title?: string;
  url?: string | null;
  resource_type?: string;
  subject?: string;
  difficulty?: string;
  description?: string | null;
  tags?: string[] | null;
  rating?: number;
  is_free?: boolean;
}

// ===== 考研资讯 =====
export interface KaoyanNewsResponse {
  id: string;
  title: string;
  summary: string | null;
  content: string | null;
  source_platform: string;
  source_url: string;
  published_at: string | null;
  crawled_at: string;
  category: string;
  tags: string[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KaoyanNewsListResponse {
  items: KaoyanNewsResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface CommentResponse {
  id: string;
  post_id: string;
  user_id: string;
  content: string;
  parent_id: string | null;
  like_count: number;
  is_deleted: boolean;
  author_nickname: string;
  created_at: string;
  updated_at: string;
}

export interface CommentCreate {
  post_id: string;
  content: string;
  parent_id?: string | null;
}

export interface CommentListResponse {
  items: CommentResponse[];
  total: number;
}

// ===== 决策副驾驶护城河（Phase D） =====
// 类型定义位于 ./decision-copilot，此处 re-export 保持单一类型入口
export * from "./decision-copilot";
