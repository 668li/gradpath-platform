// 家庭对话脚手架相关类型定义
// 与后端 app/schemas/family_dialogue.py 对齐

export type ParentArchetype =
  | "stability_first" // 稳定优先型
  | "prestige_first" // 面子优先型
  | "practical_worry" // 现实焦虑型
  | "supportive"; // 开明支持型

export type FamilyDialogueStatus = "preparing" | "practiced" | "completed";

/** 启动会话请求 */
export interface FamilyDialogueStart {
  parent_concern: string; // 父母主要担心什么
  user_choice: string; // 用户想选什么
  parent_archetype: ParentArchetype; // 父母类型
}

/** 单条论据 — 把父母的话术翻译成数据化回应 + 共情提示 */
export interface Argument {
  parent_saying: string; // 父母可能说的话
  user_response: string; // 建议回应
  data_backing: string; // 数据支撑
  empathy_note: string; // 共情提示
}

/** 模拟对话消息 */
export interface PracticeMessage {
  role: "parent" | "user";
  content: string;
}

/** 会话响应 — 含理解分析、论据、沟通技巧 */
export interface FamilyDialogueResponse {
  id: string;
  parent_concern: string;
  user_choice: string;
  parent_archetype: ParentArchetype | null;
  understanding: string; // 理解父母担忧的分析
  arguments: Argument[]; // 准备的论据
  talking_tips: string[]; // 沟通技巧
  practice_messages: PracticeMessage[]; // 模拟对话记录
  status: FamilyDialogueStatus;
  created_at: string | null;
  updated_at: string | null;
}

/** 模拟对话练习请求 */
export interface PracticeRequest {
  message: string;
}
