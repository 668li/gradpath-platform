// 决策副驾驶（Decision Copilot）类型定义
// 与后端 Phase A-C 实现的 5 个 API 模块对齐：
//   - /api/user-context
//   - /api/user-memory
//   - /api/onboarding
//   - /api/decision-pulse
//   - /api/dark-knowledge-push

// ===== 枚举 =====

export type MemoryFactType =
  | "preference"
  | "background"
  | "goal"
  | "constraint"
  | "behavior"
  | "fact";

export type OnboardingStatus = "in_progress" | "completed" | "skipped";

export type ReviewStatus = "pending" | "notified" | "completed" | "skipped" | "cancelled";

export type PushFeedback = "none" | "positive" | "negative" | "later";

// ===== 用户上下文（/api/user-context） =====

export interface ContextCareerProfile {
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
}

export interface ContextOnboarding {
  current_stage: string;
  target_direction: string;
  target_industry: string | null;
  ai_diagnosis: string | null;
  recommended_path: string[] | null;
  key_insights: string[] | null;
  completed_at: string | null;
}

export interface ContextMemoryFact {
  id: string;
  fact_type: MemoryFactType;
  fact_key: string;
  fact_value: string;
  confidence: number;
}

export interface ContextDecision {
  id: string;
  destination_type: string;
  status: string;
  decision_date: string | null;
  confidence: number;
  prediction: string | null;
  review_date: string | null;
  review_completed: boolean;
}

export interface ContextOutcomeReport {
  id: string;
  outcome_type: string;
  target_school: string | null;
  actual_school: string | null;
  satisfaction_after: number | null;
  is_public: string;
}

export interface UserContextStats {
  total_decisions: number;
  completed_reviews: number;
  pending_reviews: number;
  memory_count: number;
  avg_decision_accuracy: number;
}

export interface UserContext {
  career_profile: ContextCareerProfile | null;
  onboarding: ContextOnboarding | null;
  memory_facts: ContextMemoryFact[];
  recent_decisions: ContextDecision[];
  recent_outcome_reports: ContextOutcomeReport[];
  stats: UserContextStats | Record<string, never>;
  error?: string;
}

export interface UserContextPrompt {
  prompt: string;
}

// ===== 用户记忆（/api/user-memory） =====

export interface UserMemoryFact {
  id: string;
  fact_type: MemoryFactType;
  fact_key: string;
  fact_value: string;
  confidence: number;
  source: string;
  use_count?: number;
  user_feedback?: string;
  created_at?: string | null;
  last_used_at?: string | null;
}

export interface UserMemoryListResponse {
  items: UserMemoryFact[];
  total: number;
}

export interface AddFactRequest {
  fact_type: MemoryFactType;
  fact_key: string;
  fact_value: string;
}

export interface AddFactResponse {
  id: string;
  fact_type: MemoryFactType;
  fact_key: string;
  fact_value: string;
  confidence: number;
  source: string;
}

export interface MemoryFeedbackRequest {
  feedback: "positive" | "negative";
}

export interface MemoryFeedbackResponse {
  id: string;
  confidence: number;
  is_active: boolean;
  user_feedback: string;
}

export interface ExtractRequest {
  conversation_id?: string | null;
  messages: Record<string, unknown>[];
}

export interface ExtractResponse {
  extracted_count: number;
  items: {
    id: string;
    fact_type: MemoryFactType;
    fact_key: string;
    fact_value: string;
    confidence: number;
  }[];
}

// ===== Onboarding 首次诊断（/api/onboarding） =====

export interface OnboardingRecord {
  id: string;
  current_stage: string;
  target_direction: string;
  target_industry: string | null;
  self_assessment: Record<string, unknown>;
  status: OnboardingStatus;
  ai_diagnosis: string | null;
  recommended_path: string[] | null;
  key_insights: string[] | null;
  completed_at: string | null;
  created_at: string | null;
}

export interface OnboardingGetResponse {
  onboarding: OnboardingRecord | null;
  completed: boolean;
}

export interface OnboardingSaveRequest {
  current_stage: string;
  target_direction: string;
  target_industry?: string | null;
  self_assessment?: Record<string, unknown>;
}

export interface OnboardingStatusResponse {
  completed: boolean;
}

// ===== 决策副驾驶看板（/api/decision-pulse） =====

export interface PulseOverview {
  total_decisions: number;
  completed_reviews: number;
  pending_reviews: number;
  memory_count: number;
  avg_decision_accuracy: number;
  due_reviews: number;
  unread_pushes: number;
  active_decisions: number;
  last_updated: string;
}

export interface PulseActiveDecision {
  id: string;
  destination_type: string;
  status: string;
  decision_date: string | null;
  confidence: number;
  prediction: string | null;
  review_date: string | null;
  reasoning: string | null;
}

export interface PulseReviewItem {
  id: string;
  decision_id: string;
  scheduled_at: string | null;
  status: ReviewStatus;
  is_overdue: boolean;
  days_until_due: number | null;
}

export interface PulseDarkKnowledgeItem {
  push_id: string;
  dark_knowledge_id: string;
  stage: string;
  pushed_at: string | null;
  read_at: string | null;
  is_read: boolean;
  feedback: PushFeedback;
  title: string;
  category: string;
  content: string;
  importance: "critical" | "high" | "medium" | "low";
  actionable_advice: string | null;
}

export interface PulseMemoryFact {
  id: string;
  fact_type: MemoryFactType;
  fact_key: string;
  fact_value: string;
  confidence: number;
  source: string;
  use_count: number;
  user_feedback: string;
  created_at: string | null;
}

export interface PulseFull {
  overview: PulseOverview;
  active_decisions: PulseActiveDecision[];
  review_queue: PulseReviewItem[];
  dark_knowledge_feed: PulseDarkKnowledgeItem[];
  memory_facts: PulseMemoryFact[];
}

export interface PulseListResponse<T> {
  items: T[];
}

// ===== 暗知识推送（/api/dark-knowledge-push） =====

export interface DarkKnowledgePush {
  id: string;
  user_id: string;
  dark_knowledge_id: string;
  stage: string;
  push_reason: string;
  pushed_at: string | null;
  read_at: string | null;
  is_read: boolean;
  feedback: PushFeedback;
  feedback_notes: string | null;
  rating: number | null;
}

export interface DarkKnowledgePushListResponse {
  items: DarkKnowledgePush[];
  total: number;
}

export interface DarkKnowledgeUnreadCount {
  count: number;
}

export interface DarkKnowledgePushRequest {
  stage?: string | null;
  limit?: number;
}

export interface DarkKnowledgePushTriggerResponse {
  pushed_count: number;
  items: DarkKnowledgePush[];
}

export interface DarkKnowledgeFeedbackRequest {
  feedback: "positive" | "negative" | "later";
  rating?: number | null;
  notes?: string | null;
}
