import type {
  PaginatedResponse,
  RetrospectiveResponse,
  RetroCreate,
  RetroUpdate,
  RetroDraft,
  AIRetroDraftRequest,
  AIRetroDraft,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== 复盘深化（2026-09-25）：原则库 / Try 行动卡 / 事实回放 / AI 引导 =====

export interface RetroPrinciple {
  id: string;
  trigger_scene: string;
  action: string;
  rationale: string | null;
  scene_tags: string[];
  status: "draft" | "verified" | "invalid";
  verify_count: number;
  source_retro_id: string | null;
  source_title: string | null;
  is_example: boolean;
  next_review_at: string | null;
  created_at: string | null;
}

export interface RetroActionCard {
  id: string;
  retro_id: string;
  content: string;
  trigger_scene: string;
  status: "pending" | "effective" | "ineffective" | "not_met";
  review_due_at: string;
  reviewed_at: string | null;
  review_note: string | null;
  principle_id: string | null;
}

export interface ReplayData {
  period: { start: string; end: string };
  node_feedbacks: Array<{ node_title: string; status: string; feedback_at: string | null }>;
  career_events: Array<{
    id: string;
    event_date: string;
    event_type: string;
    title: string;
    has_star: boolean;
    mood: number | null;
    reflection: string | null;
  }>;
  condition_summary: Record<string, unknown> | null;
  due_actions: RetroActionCard[];
  counts: { node_done: number; node_uncertain: number; node_skipped: number; events: number };
}

export interface ReflectTurn {
  stage: "fact" | "analysis" | "insight" | "next_action" | "done";
  question: string;
  options: string[];
  acknowledge: string;
  sharp_rebuttal: string;
}

// ===== Retrospectives =====
export const retrospectivesApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    request<PaginatedResponse<RetrospectiveResponse>>(
      `/api/retrospectives${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  get: (id: string) => request<RetrospectiveResponse>(`/api/retrospectives/${id}`),
  create: (body: RetroCreate) =>
    request<RetrospectiveResponse>("/api/retrospectives", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: RetroUpdate) =>
    request<RetrospectiveResponse>(`/api/retrospectives/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/retrospectives/${id}`, { method: "DELETE" }),
  draft: (period_start: string, period_end: string) =>
    request<RetroDraft>(
      `/api/retrospectives/draft${buildQuery({ period_start, period_end })}`,
    ),
  aiDraft: (body: AIRetroDraftRequest) =>
    request<AIRetroDraft>("/api/retrospectives/ai-draft", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // ── 事实回放 ──
  replay: (period_start: string, period_end: string) =>
    request<ReplayData>(
      `/api/retrospectives/replay${buildQuery({ period_start, period_end })}`,
    ),

  // ── 原则库 ──
  listPrinciples: () =>
    request<{ principles: RetroPrinciple[] }>("/api/retrospectives/principles"),
  createPrinciple: (body: {
    trigger_scene: string;
    action: string;
    rationale?: string | null;
    scene_tags?: string[];
    source_retro_id?: string | null;
  }) =>
    request<RetroPrinciple>("/api/retrospectives/principles", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updatePrinciple: (
    id: string,
    body: { trigger_scene?: string; action?: string; rationale?: string | null; scene_tags?: string[] },
  ) =>
    request<RetroPrinciple>(`/api/retrospectives/principles/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  verifyPrinciple: (id: string, verdict: "again" | "ineffective" | "pending", note?: string) =>
    request<RetroPrinciple>(`/api/retrospectives/principles/${id}/verify`, {
      method: "POST",
      body: JSON.stringify({ verdict, note: note ?? null }),
    }),
  removePrinciple: (id: string) =>
    request<void>(`/api/retrospectives/principles/${id}`, { method: "DELETE" }),

  // ── Try 行动卡 ──
  createActions: (retro_id: string, items: Array<{ content: string; trigger_scene: string }>) =>
    request<{ actions: RetroActionCard[] }>("/api/retrospectives/actions", {
      method: "POST",
      body: JSON.stringify({ retro_id, items }),
    }),
  dueActions: (include_future_days = 14) =>
    request<{ actions: RetroActionCard[] }>(
      `/api/retrospectives/actions/due${buildQuery({ include_future_days: String(include_future_days) })}`,
    ),
  reviewAction: (id: string, verdict: "effective" | "ineffective" | "not_met", note?: string) =>
    request<{ action: RetroActionCard; upgraded_principle: RetroPrinciple | null }>(
      `/api/retrospectives/actions/${id}/review`,
      { method: "POST", body: JSON.stringify({ verdict, note: note ?? null }) },
    ),

  // ── AI 引导反思 / 原则提炼 ──
  reflect: (body: {
    messages: Array<{ role: "user" | "coach"; content: string }>;
    period_start?: string | null;
    period_end?: string | null;
  }) =>
    request<ReflectTurn>("/api/retrospectives/reflect", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  principleDraft: (body: {
    retro_content: string;
    source_retro_id?: string | null;
    period_start?: string | null;
    period_end?: string | null;
  }) =>
    request<{ principles: Array<{ trigger_scene: string; action: string; rationale: string | null; scene_tags: string[] }> }>(
      "/api/retrospectives/principle-draft",
      { method: "POST", body: JSON.stringify(body) },
    ),
};