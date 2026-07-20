import type {
  Conversation,
  PaginatedResponse,
  Message,
  SendMessageRequest,
  SendMessageResponse,
  // 修复: 配合 types/index.ts 中 SkillInfo 重命名为 ChatSkillInfo
  ChatSkillInfo,
} from "@/types";
import { request, buildQuery } from "./client";

// ===== AI 职业管家 — 对话 =====
export const chatApi = {
  createConversation: (title?: string) =>
    request<Conversation>("/api/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title: title || "新对话" }),
    }),
  listConversations: (params?: { page?: number; page_size?: number }) =>
    request<PaginatedResponse<Conversation>>(
      `/api/chat/conversations${buildQuery((params as Record<string, string | undefined | null>) || {})}`,
    ),
  getMessages: (conversationId: string) =>
    request<Message[]>(`/api/chat/conversations/${conversationId}/messages`),
  sendMessage: (conversationId: string, body: SendMessageRequest) =>
    request<SendMessageResponse>(
      `/api/chat/conversations/${conversationId}/messages`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  updateTitle: (conversationId: string, title: string) =>
    request<Conversation>(`/api/chat/conversations/${conversationId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (conversationId: string) =>
    request<void>(`/api/chat/conversations/${conversationId}`, {
      method: "DELETE",
    }),
  listSkills: () => request<ChatSkillInfo[]>("/api/chat/skills"),
};