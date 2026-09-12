import { request } from "./client";
import type {
  MyTimelineExam,
  NodeFeedbackStatus,
  TimelineExam,
  TimelineExamDetail,
  TimelineNode,
} from "@/types/exam-timeline";

const BASE = "/api/civil-service/timeline";

export const examTimelineApi = {
  /** C1 考次列表（公开） */
  listExams: (track?: string) =>
    request<TimelineExam[]>(track ? `${BASE}/exams?track=${encodeURIComponent(track)}` : `${BASE}/exams`),

  /** C2 考次详情+12 节点（公开） */
  getExam: (code: string) => request<TimelineExamDetail>(`${BASE}/exams/${encodeURIComponent(code)}`),

  /** C3 订阅（登录；重复 409） */
  subscribe: (code: string) =>
    request<{ exam_code: string; subscribed: boolean; notify_channels: string[] }>(
      `${BASE}/exams/${encodeURIComponent(code)}/subscribe`,
      { method: "POST" },
    ),

  /** C4 软退订（登录，保留回传史） */
  unsubscribe: (code: string) =>
    request<void>(`${BASE}/exams/${encodeURIComponent(code)}/subscription`, { method: "DELETE" }),

  /** C5 我的订阅+进度（登录） */
  mine: () => request<MyTimelineExam[]>(`${BASE}/me`),

  /** C6 节点回传（登录，须已订阅；跨考 404） */
  feedback: (nodeId: string, status: NodeFeedbackStatus) =>
    request<TimelineNode>(`${BASE}/nodes/${encodeURIComponent(nodeId)}/feedback`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),

  /** C7 单节点深链（公开） */
  getNode: (nodeId: string) => request<TimelineNode>(`${BASE}/nodes/${encodeURIComponent(nodeId)}`),
};
