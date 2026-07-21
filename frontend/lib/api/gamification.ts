import type { GamificationProfile, UserSetting, StreakStats, StreakCheckInRequest, StreakCheckInResponse } from "@/types";
import { request } from "./client";

// ===== 游戏化 =====
export const gamificationApi = {
  profile: () => request<GamificationProfile>("/api/gamification/profile"),
  getSettings: () => request<UserSetting>("/api/gamification/settings"),
  updateSettings: (body: { share_skills_enabled: boolean }) =>
    request<UserSetting>("/api/gamification/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};

// ===== 护城河功能：连续打卡 =====
export const streaksApi = {
  getStats: () => request<StreakStats>("/api/streaks/stats"),
  checkin: (body: StreakCheckInRequest) =>
    request<StreakCheckInResponse>("/api/streaks/checkin", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  restDay: () =>
    request<{ streak_count: number; message: string }>("/api/streaks/rest-day", {
      method: "POST",
    }),
  redeem: () =>
    request<{ streak_count: number; message: string; redeemed: boolean }>("/api/streaks/redeem", {
      method: "POST",
    }),
};