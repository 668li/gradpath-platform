import type { SkillResponse, SkillCreate, SkillUpdate, SkillStats, SkillListResponse, SkillInfo } from "@/types";
import { request } from "./client";

// ===== Skills =====
export const skillsApi = {
  tree: () => request<SkillResponse[]>("/api/skills"),
  get: (id: string) => request<SkillResponse>(`/api/skills/${id}`),
  create: (body: SkillCreate) =>
    request<SkillResponse>("/api/skills", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (id: string, body: SkillUpdate) =>
    request<SkillResponse>(`/api/skills/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    request<void>(`/api/skills/${id}`, { method: "DELETE" }),
  stats: () => request<SkillStats>("/api/skills/stats"),
  // 批量获取技能（消除前端 N+1 调用，仅返回当前用户的技能）
  batch: (ids: string[]) =>
    request<SkillResponse[]>(`/api/skills/batch`, {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
};

// ===== Skill 管理 =====
export const skillApi = {
  /** 列出所有 skill */
  list: () => request<SkillListResponse>("/api/skill-toolbox"),
  /** 获取指定 skill 详情 */
  get: (name: string) => request<SkillInfo>(`/api/skill-toolbox/${name}`),
  /** 按分类列出 skill */
  byCategory: (category: string) =>
    request<SkillListResponse>(`/api/skill-toolbox/category/${category}`),
};