/**
 * 对话页深链参数解析（speckit 003 FR5）。
 *
 * 纯函数、可单测：从 URL query 读出预填文本与预选 skill。
 * 安全边界：prefill 只进输入框 state（React 转义，不入 HTML）、
 * 绝不自动发送（spec A4）；skill 走白名单，深链不能把任意串注入 skillHint。
 */
export interface ChatDeepLinkParams {
  prefill: string;
  skill: string | null;
}

/** 允许预选的 skill 白名单（与后端 chat_deep_link._SKILL 对齐） */
const ALLOWED_SKILLS = new Set(["timeline_companion"]);

/**
 * 解析对话页深链 query。合法形态：
 * `/chat?prefill=<文案>&skill=timeline_companion&src=reminder&node=<id>`
 *
 * 返回 null 表示不是合法深链（无 prefill 或缺少 src=reminder 溯源标记），
 * 页面按普通进入处理。
 */
export function readChatDeepLink(search: string): ChatDeepLinkParams | null {
  if (!search) return null;
  const sp = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const prefill = (sp.get("prefill") || "").trim();
  if (!prefill || sp.get("src") !== "reminder") return null;
  const skill = sp.get("skill");
  return { prefill, skill: skill && ALLOWED_SKILLS.has(skill) ? skill : null };
}
