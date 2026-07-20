import { request, buildQuery } from "./client";
import type {
  AddFactRequest,
  AddFactResponse,
  DarkKnowledgeFeedbackRequest,
  DarkKnowledgePush,
  DarkKnowledgePushListResponse,
  DarkKnowledgePushRequest,
  DarkKnowledgePushTriggerResponse,
  DarkKnowledgeUnreadCount,
  ExtractRequest,
  ExtractResponse,
  MemoryFeedbackRequest,
  MemoryFeedbackResponse,
  OnboardingGetResponse,
  OnboardingRecord,
  OnboardingSaveRequest,
  OnboardingStatusResponse,
  PulseActiveDecision,
  PulseDarkKnowledgeItem,
  PulseFull,
  PulseMemoryFact,
  PulseOverview,
  PulseReviewItem,
  UserContext,
  UserContextPrompt,
  UserMemoryFact,
  UserMemoryListResponse,
} from "../../types/decision-copilot";

// ===== 用户上下文 API =====

export const userContextApi = {
  /** 获取聚合用户上下文（画像+诊断+记忆+决策+统计） */
  getContext: () => request<UserContext>("/api/user-context"),

  /** 获取 AI 注入用 prompt 文本 */
  getPrompt: () => request<UserContextPrompt>("/api/user-context/prompt"),
};

// ===== 用户记忆 API =====

export const userMemoryApi = {
  /** 检索用户记忆事实 */
  list: (params?: { fact_type?: string; limit?: number }) =>
    request<UserMemoryListResponse>(
      `/api/user-memory${buildQuery((params as Record<string, string | number | undefined>) || {})}`,
    ),

  /** 用户主动添加记忆事实 */
  add: (data: AddFactRequest) =>
    request<AddFactResponse>("/api/user-memory", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** 用户反馈调整置信度 */
  feedback: (factId: string, data: MemoryFeedbackRequest) =>
    request<MemoryFeedbackResponse>(`/api/user-memory/${factId}/feedback`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** 删除记忆事实（软删除） */
  remove: (factId: string) =>
    request<void>(`/api/user-memory/${factId}`, { method: "DELETE" }),

  /** 从对话消息中抽取记忆事实（触发 LLM） */
  extract: (data: ExtractRequest) =>
    request<ExtractResponse>("/api/user-memory/extract", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ===== Onboarding 首次诊断 API =====

export const onboardingApi = {
  /** 查询用户 onboarding 状态 */
  get: () => request<OnboardingGetResponse>("/api/onboarding"),

  /** 检查是否已完成 onboarding */
  getStatus: () => request<OnboardingStatusResponse>("/api/onboarding/status"),

  /** 保存诊断答案（状态为 in_progress，不生成 AI 诊断） */
  save: (data: OnboardingSaveRequest) =>
    request<OnboardingRecord>("/api/onboarding", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** 生成 AI 诊断 + 推荐路径 */
  generate: () =>
    request<OnboardingRecord>("/api/onboarding/generate", { method: "POST" }),

  /** 跳过 onboarding */
  skip: () => request<OnboardingRecord>("/api/onboarding/skip", { method: "POST" }),
};

// ===== 决策副驾驶看板 API =====

export const decisionPulseApi = {
  /** 完整看板数据（一次调用返回所有面板） */
  getFull: () => request<PulseFull>("/api/decision-pulse"),

  /** 总览统计 */
  getOverview: () => request<PulseOverview>("/api/decision-pulse/overview"),

  /** 进行中决策列表 */
  getActiveDecisions: (limit = 10) =>
    request<{ items: PulseActiveDecision[] }>(
      `/api/decision-pulse/active-decisions${buildQuery({ limit })}`,
    ),

  /** 待回顾决策队列 */
  getReviewQueue: (limit = 10) =>
    request<{ items: PulseReviewItem[] }>(
      `/api/decision-pulse/review-queue${buildQuery({ limit })}`,
    ),

  /** 暗知识推送流 */
  getDarkKnowledgeFeed: (limit = 10) =>
    request<{ items: PulseDarkKnowledgeItem[] }>(
      `/api/decision-pulse/dark-knowledge-feed${buildQuery({ limit })}`,
    ),

  /** AI 记忆面板 */
  getMemoryFacts: (limit = 20) =>
    request<{ items: PulseMemoryFact[] }>(
      `/api/decision-pulse/memory-facts${buildQuery({ limit })}`,
    ),
};

// ===== 暗知识推送 API =====

export const darkKnowledgePushApi = {
  /** 查询推送历史 */
  list: (params?: { only_unread?: boolean; limit?: number }) => {
    const query: Record<string, string | number | undefined> = {};
    if (params?.only_unread) query.only_unread = "true";
    if (params?.limit !== undefined) query.limit = params.limit;
    return request<DarkKnowledgePushListResponse>(
      `/api/dark-knowledge-push${buildQuery(query)}`,
    );
  },

  /** 未读推送数 */
  getUnreadCount: () =>
    request<DarkKnowledgeUnreadCount>("/api/dark-knowledge-push/unread-count"),

  /** 手动触发推送（用户主动获取新暗知识） */
  trigger: (data: DarkKnowledgePushRequest) =>
    request<DarkKnowledgePushTriggerResponse>("/api/dark-knowledge-push/push", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** 标记推送为已读 */
  markRead: (pushId: string) =>
    request<DarkKnowledgePush>(`/api/dark-knowledge-push/${pushId}/read`, {
      method: "POST",
    }),

  /** 记录推送反馈 */
  feedback: (pushId: string, data: DarkKnowledgeFeedbackRequest) =>
    request<DarkKnowledgePush>(`/api/dark-knowledge-push/${pushId}/feedback`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// 兼容类型重导出，方便组件直接从 api 模块引入
export type {
  UserContext,
  UserContextPrompt,
  UserMemoryFact,
  UserMemoryListResponse,
  AddFactRequest,
  AddFactResponse,
  MemoryFeedbackRequest,
  MemoryFeedbackResponse,
  ExtractRequest,
  ExtractResponse,
  OnboardingGetResponse,
  OnboardingRecord,
  OnboardingSaveRequest,
  OnboardingStatusResponse,
  PulseOverview,
  PulseActiveDecision,
  PulseReviewItem,
  PulseDarkKnowledgeItem,
  PulseMemoryFact,
  PulseFull,
  DarkKnowledgePush,
  DarkKnowledgePushListResponse,
  DarkKnowledgeUnreadCount,
  DarkKnowledgePushRequest,
  DarkKnowledgePushTriggerResponse,
  DarkKnowledgeFeedbackRequest,
} from "../../types/decision-copilot";
