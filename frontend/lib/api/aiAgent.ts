import { request } from "./client";

// ===== AI Agent — 统一端点 =====
export interface AgentSource {
  type: "db" | "web";
  title: string;
  content: string;
  url: string;
}

export interface AgentResponse {
  answer: string;
  sources: AgentSource[];
  confidence: number;
}

export interface AgentRequest {
  question: string;
  search_web?: boolean;
  context?: string;
}

export const aiAgentApi = {
  ask: (params: AgentRequest) =>
    request<AgentResponse>("/api/ai/agent", {
      method: "POST",
      body: JSON.stringify({
        question: params.question,
        search_web: params.search_web ?? true,
        ...(params.context && { context: params.context }),
      }),
    }),
};
