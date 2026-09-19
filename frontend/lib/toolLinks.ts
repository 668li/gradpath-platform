// 外链目录（009 T4）：考研/考公两线复用的静态常量，零后端零迁移。
//
// 收录纪律（09-19 拍板④）：站点清单 = 用户点名制——
//   用户点名 → 执行会话实测（可达性/robots/性质）→ 回报 → 用户确认 → 入目录。
// 零预填：侦察档案（chinakaoyan/yanxian/考研帮/kaoyan365/eol 五站）仅备查，
// 不构成添加依据；搬运入库禁。
export type ToolLinkCategory = "official" | "commercial" | "ugc" | "archive";

export interface ToolLink {
  name: string;
  url: string;
  category: ToolLinkCategory;
  /** 一句话定位（必填）：这站是干什么的 */
  note: string;
  /** ugc / archive 类必须附风险注记 */
  riskNote?: string;
}

export const TOOL_CATEGORY_LABELS: Record<ToolLinkCategory, string> = {
  official: "官方",
  commercial: "商业",
  ugc: "社区/UGC",
  archive: "存档",
};

// 初始为空：等用户点名第一个站点后在此登记（点名制，见文件头注释）。
export const TOOL_LINKS: ToolLink[] = [];
