// 统一色板：集中所有图表使用的颜色，避免散落在各组件里。
// brand/* 为设计系统 CSS 变量；其余为雷达 / 饼图 / 折线固定的具体色值。

// 品牌色阶（柱状体渐变用）— 直接使用 tailwind.config.ts 中的 brand hex
export const BRAND_SCALE = [
  "#38a887", // brand-400
  "#1a8c6e", // brand-500
  "#0d7159", // brand-600
  "#0a5a48", // brand-700
  "#094838", // brand-800
];

// 通用折线 / 主色 — 直接 hex，与 tailwind.config.ts 对齐
export const BRAND_LINE = "#0d7159"; // brand-600
export const GRID_COLOR = "#f5f3ec"; // paper-200
export const TICK_COLOR = "#7a7468"; // ink-400

// 雷达对比多系列配色（院校对比 / 技能 / 霍兰德 / 人生轮复用）
export const RADAR_COLORS = [
  "#0d7159", // brand-600
  "#3377f6",
  "#d97706",
  "#dc2626",
  "#7c3aed",
];

// 饼图分类配色（普通 name/value 型数据）
export const PIE_COLORS = [
  "#3377f6",
  "#16a34a",
  "#d97706",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
  "#db2777",
  "#64748b",
];

// 毕业去向配色（按 RATE key 索引）
export const RATE_COLORS: Record<string, string> = {
  employment: "#3377f6",
  further_study: "#16a34a",
  civil_service: "#d97706",
  abroad: "#7c3aed",
  startup: "#dc2626",
  gap_year: "#64748b",
};

// 毕业去向中文标签
export const RATE_LABEL: Record<string, string> = {
  employment: "就业",
  further_study: "升学",
  civil_service: "考公",
  abroad: "出国",
  startup: "创业",
  gap_year: "间隔年",
};

// 中性灰（缺色兜底）
export const FALLBACK_COLOR = "#999";

// 工具：按索引取色板颜色
export function paletteColor(palette: string[], i: number): string {
  return palette[i % palette.length];
}
