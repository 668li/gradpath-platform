import { request } from "./client";
import type {
  FamilyDialogueStart,
  FamilyDialogueResponse,
  PracticeMessage,
  PracticeRequest,
} from "@/types/family-dialogue";

const BASE = "/api/family-dialogue";

export const familyDialogueApi = {
  /** 启动会话：理解父母 + 准备论据 */
  start: (data: FamilyDialogueStart) =>
    request<FamilyDialogueResponse>(BASE + "/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  /** 获取单条会话详情 */
  getSession: (sessionId: string) =>
    request<FamilyDialogueResponse>(BASE + `/session/${sessionId}`),

  /** 模拟对话练习：用户输入要说的话，AI 扮演父母回复 */
  practice: (sessionId: string, message: string) =>
    request<PracticeMessage>(BASE + `/session/${sessionId}/practice`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message } satisfies PracticeRequest),
    }),

  /** 获取用户的历史会话（按时间倒序） */
  getHistory: () => request<FamilyDialogueResponse[]>(BASE + "/history"),
};
