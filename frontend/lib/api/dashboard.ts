import type { DashboardOverview, WeeklyRecap } from "@/types";
import { request } from "./client";

// ===== Dashboard =====
export const dashboardApi = {
  overview: () => request<DashboardOverview>("/api/dashboard/overview"),
  weeklyRecap: () => request<WeeklyRecap>("/api/dashboard/weekly-recap"),
  personalIntel: () => request<any>("/api/dashboard/personal-intel"),
};