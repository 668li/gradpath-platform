import type {
  DecisionStatus,
  DestinationType,
  EventType,
  PeriodType,
} from "@/types";

// ===== 去向决策 =====
export const DESTINATION_TYPE_LABEL: Record<DestinationType, string> = {
  employment: "就业",
  postgrad: "考研",
  civil_service: "考公",
  abroad: "出国",
  phd: "读博",
  startup: "创业",
  gap_year: "间隔年",
};

export const DESTINATION_TYPES: DestinationType[] = [
  "employment",
  "postgrad",
  "civil_service",
  "abroad",
  "phd",
  "startup",
  "gap_year",
];

export const DECISION_STATUS_LABEL: Record<DecisionStatus, string> = {
  planned: "计划中",
  confirmed: "已确认",
  executed: "已执行",
  changed: "已变更",
};

export const DECISION_STATUSES: DecisionStatus[] = [
  "planned",
  "confirmed",
  "executed",
  "changed",
];

/**
 * 每种去向类型对应的 details 字段配置，用于动态渲染表单。
 * key=字段名, label=中文标签, placeholder=提示
 */
export interface DetailFieldConfig {
  key: string;
  label: string;
  placeholder?: string;
  type?: "text" | "select";
  options?: { value: string; label: string }[];
}

export const DESTINATION_DETAIL_FIELDS: Record<DestinationType, DetailFieldConfig[]> = {
  employment: [
    { key: "company", label: "公司", placeholder: "如：腾讯" },
    { key: "position", label: "职位", placeholder: "如：后端开发工程师" },
    { key: "city", label: "城市", placeholder: "如：深圳" },
    { key: "salary_range", label: "薪资范围", placeholder: "如：25-30k" },
    {
      key: "company_nature",
      label: "公司性质",
      type: "select",
      options: [
        { value: "国企", label: "国企" },
        { value: "民企", label: "民企" },
        { value: "外企", label: "外企" },
        { value: "事业单位", label: "事业单位" },
      ],
    },
  ],
  postgrad: [
    { key: "target_school", label: "目标院校", placeholder: "如：清华大学" },
    { key: "target_major", label: "目标专业", placeholder: "如：计算机科学与技术" },
    {
      key: "result",
      label: "结果",
      type: "select",
      options: [
        { value: "pending", label: "待定" },
        { value: "admitted", label: "已录取" },
        { value: "rejected", label: "未录取" },
      ],
    },
  ],
  civil_service: [
    { key: "agency", label: "单位", placeholder: "如：国家税务总局" },
    { key: "position", label: "职位", placeholder: "如：科员" },
    {
      key: "level",
      label: "层级",
      type: "select",
      options: [
        { value: "central", label: "中央" },
        { value: "provincial", label: "省级" },
        { value: "municipal", label: "市级" },
      ],
    },
  ],
  abroad: [
    { key: "country", label: "国家", placeholder: "如：美国" },
    { key: "school", label: "学校", placeholder: "如：Stanford University" },
    { key: "program", label: "项目", placeholder: "如：MSCS" },
    {
      key: "degree",
      label: "学位",
      type: "select",
      options: [
        { value: "master", label: "硕士" },
        { value: "phd", label: "博士" },
      ],
    },
  ],
  phd: [
    { key: "school", label: "学校", placeholder: "如：北京大学" },
    { key: "advisor", label: "导师", placeholder: "如：张教授" },
    { key: "field", label: "研究方向", placeholder: "如：人工智能" },
  ],
  startup: [
    { key: "company_name", label: "公司名称", placeholder: "如：某某科技" },
    { key: "role", label: "角色", placeholder: "如：创始人" },
    { key: "field", label: "领域", placeholder: "如：教育科技" },
  ],
  gap_year: [
    { key: "plan", label: "计划", placeholder: "描述你的间隔年计划" },
  ],
};

// ===== 职业事件 =====
export const EVENT_TYPE_LABEL: Record<EventType, string> = {
  onboard: "入职",
  leave: "离职",
  promotion: "晋升",
  transfer: "转岗",
  skill_acquired: "技能习得",
  project_done: "项目完成",
  certification: "获得证书",
  other: "其他",
};

export const EVENT_TYPES: EventType[] = [
  "onboard",
  "leave",
  "promotion",
  "transfer",
  "skill_acquired",
  "project_done",
  "certification",
  "other",
];

// 事件类型对应的颜色（用于时间线/Tab）
export const EVENT_TYPE_COLOR: Record<EventType, string> = {
  onboard: "#16a34a",
  leave: "#dc2626",
  promotion: "#d97706",
  transfer: "#0891b2",
  skill_acquired: "#7c3aed",
  project_done: "#2563eb",
  certification: "#db2777",
  other: "#64748b",
};

// ===== 复盘 =====
export const PERIOD_TYPE_LABEL: Record<PeriodType, string> = {
  annual: "年度",
  quarterly: "季度",
  project: "项目",
  custom: "自定义",
};

export const PERIOD_TYPES: PeriodType[] = [
  "annual",
  "quarterly",
  "project",
  "custom",
];

// 饼图配色
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

// ===== 就业去向分布标签 =====
export const RATE_LABEL: Record<string, string> = {
  employment: "就业",
  further_study: "升学",
  civil_service: "考公",
  abroad: "出国",
  startup: "创业",
  gap_year: "间隔年",
};

export const RATE_COLORS: Record<string, string> = {
  employment: "#3377f6",
  further_study: "#16a34a",
  civil_service: "#d97706",
  abroad: "#7c3aed",
  startup: "#dc2626",
  gap_year: "#64748b",
};

// ===== 社区数据 =====
// 社区去向类型（与 RATE_LABEL 的 key 一致，复用 RATE_LABEL / RATE_COLORS 展示）
export const COMMUNITY_DESTINATION_TYPES = [
  "employment",
  "further_study",
  "civil_service",
  "abroad",
  "startup",
  "gap_year",
];

export const DEGREE_OPTIONS = [
  { value: "bachelor", label: "本科" },
  { value: "master", label: "硕士" },
  { value: "phd", label: "博士" },
];

export const DEGREE_LABEL: Record<string, string> = {
  bachelor: "本科",
  master: "硕士",
  phd: "博士",
};

export const SALARY_RANGE_OPTIONS = [
  { value: "below_8k", label: "8k以下" },
  { value: "8k_15k", label: "8k-15k" },
  { value: "15k_25k", label: "15k-25k" },
  { value: "25k_50k", label: "25k-50k" },
  { value: "above_50k", label: "50k以上" },
  { value: "prefer_not", label: "不便透露" },
];

export const SALARY_RANGE_LABEL: Record<string, string> = {
  below_8k: "8k以下",
  "8k_15k": "8k-15k",
  "15k_25k": "15k-25k",
  "25k_50k": "25k-50k",
  above_50k: "50k以上",
  prefer_not: "不便透露",
};

// ===== 面试经验 =====
export const INTERVIEW_DIMENSION_LABEL: Record<string, string> = {
  algorithm: "算法/编程",
  system_design: "系统设计",
  project_depth: "项目深度",
  culture_fit: "文化匹配",
  communication: "沟通表达",
  domain: "专业知识",
  behavior: "行为面试",
};

export const INTERVIEW_DIMENSIONS = [
  "algorithm",
  "system_design",
  "project_depth",
  "culture_fit",
  "communication",
  "domain",
  "behavior",
];

export const INTERVIEW_RESULT_LABEL: Record<string, string> = {
  offer: "拿到 offer",
  rejected: "未通过",
  pending: "进行中",
};

export const INTERVIEW_RESULTS = ["offer", "rejected", "pending"];

export const INTERVIEW_RESULT_COLOR: Record<string, string> = {
  offer: "#16a34a",
  rejected: "#dc2626",
  pending: "#d97706",
};

// ===== 数据管道 =====
export const PARSE_STATUS_LABEL: Record<string, string> = {
  pending: "待解析",
  parsed: "已解析",
  failed: "失败",
  reviewed: "已审核",
  published: "已发布",
};

export const PARSE_STATUS_COLOR: Record<string, string> = {
  pending: "#d97706",
  parsed: "#2563eb",
  failed: "#dc2626",
  reviewed: "#7c3aed",
  published: "#16a34a",
};

export const SOURCE_TYPE_LABEL: Record<string, string> = {
  crawl: "爬虫抓取",
  upload: "文件上传",
  api: "API对接",
};

export const CONTENT_TYPE_LABEL: Record<string, string> = {
  html: "HTML",
  pdf: "PDF",
  excel: "Excel",
  csv: "CSV",
  json: "JSON",
};
