import type {
  AssessmentType,
  Question,
  AssessmentSubmit,
  AssessmentResponse,
  LifeWheelSubmit,
  LifeWheelSnapshot,
  LifeWheelDimension,
} from "@/types";
import { request } from "./client";

// ===== 职业测评 =====
export const assessmentApi = {
  getQuestions: (type: AssessmentType = "holland") =>
    request<Question[]>(`/api/assessment/questions?type=${type}`),
  submit: (body: AssessmentSubmit) =>
    request<AssessmentResponse>("/api/assessment/submit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getResult: () => request<AssessmentResponse | null>("/api/assessment/result"),
  getHistory: () => request<AssessmentResponse[]>("/api/assessment/history"),
};

// ===== 护城河功能：人生平衡轮 =====
export const lifeWheelApi = {
  submit: (body: LifeWheelSubmit) =>
    request<LifeWheelSnapshot>("/api/life-wheel/submit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getLatest: () => request<LifeWheelSnapshot | null>("/api/life-wheel/latest"),
  getHistory: () => request<LifeWheelSnapshot[]>("/api/life-wheel/history"),
  getDimensions: () => request<LifeWheelDimension[]>("/api/life-wheel/dimensions"),
  analyze: (snapshotId: string) =>
    request<{ ai_analysis: string }>("/api/life-wheel/analyze", {
      method: "POST",
      body: JSON.stringify({ snapshot_id: snapshotId }),
    }),
};