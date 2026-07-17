import type { GamificationProfile, UserSetting, StreakStats } from "@/types";
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
};