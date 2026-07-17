import type { RegisterRequest, LoginRequest, TokenResponse, UserResponse } from "@/types";
import { request } from "./client";

// ===== Auth =====
export const authApi = {
  register: (body: RegisterRequest) =>
    request<UserResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: LoginRequest) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request<UserResponse>("/api/auth/me"),
};