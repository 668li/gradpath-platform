import { request } from "./client";

/** 用户自带 LLM API 配置（BYOK） */
export interface UserLlmConfigResponse {
  provider: string;
  base_url: string;
  model: string;
  api_key_masked: string;
  is_enabled: boolean;
  updated_at: string | null;
}

export interface UserLlmConfigSaveRequest {
  provider: string;
  base_url: string;
  model: string;
  api_key?: string;
  is_enabled?: boolean;
}

export interface UserLlmVerifyResponse {
  ok: boolean;
  message: string;
  latency_ms: number | null;
}

// ===== AI 对话服务（BYOK）=====
export const userLlmConfigApi = {
  getConfig: () =>
    request<UserLlmConfigResponse | null>("/api/user-llm-config"),
  saveConfig: (body: UserLlmConfigSaveRequest) =>
    request<UserLlmConfigResponse>("/api/user-llm-config", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteConfig: () =>
    request<void>("/api/user-llm-config", { method: "DELETE" }),
  verifyConfig: (body: UserLlmConfigSaveRequest) =>
    request<UserLlmVerifyResponse>("/api/user-llm-config/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
