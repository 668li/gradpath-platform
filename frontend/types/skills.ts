// 能力地图（Skill Map）类型定义
// 注意：本文件独立于 types/index.ts，不通过 index.ts re-export，
// 避免与 index.ts 中求职定位模块的 SkillGap 类型冲突。
// 调用方直接 import from "@/types/skills"。

/** 技能差距状态 */
export type SkillGapStatus = "mastered" | "needs_improvement" | "needs_new";

/** 学习资源类型 */
export type LearningResourceType = "course" | "book" | "article";

/** 学习资源 */
export interface SkillLearningResource {
  title: string;
  url: string;
  type: LearningResourceType;
}

/** 单项技能差距 */
export interface SkillGap {
  skill_id: string;
  skill_name: string;
  /** 硬技能 / 软技能 */
  category: "hard" | "soft";
  /** 0-100 用户当前水平 */
  current_level: number;
  /** 0-100 目标岗位要求 */
  required_level: number;
  /** required - current，负数表示超出 */
  gap: number;
  /** mastered: current >= required; needs_improvement: 0 < current < required; needs_new: current == 0 */
  status: SkillGapStatus;
  /** 目标岗位 */
  target_role?: string;
  /** 推荐学习资源 */
  learning_resources?: SkillLearningResource[];
}

/** 能力地图聚合数据 */
export interface SkillMap {
  /** 目标岗位 */
  target_role: string;
  /** 技能差距列表 */
  skills: SkillGap[];
  /** 0-100 整体匹配度 */
  overall_match: number;
  /** 已掌握数量 */
  mastered_count: number;
  /** 需提升数量 */
  needs_improvement_count: number;
  /** 需新增数量 */
  needs_new_count: number;
}

/** 预设目标岗位 */
export const TARGET_ROLES = [
  "前端工程师",
  "后端工程师",
  "全栈工程师",
  "数据分析师",
  "产品经理",
  "UI设计师",
  "考研方向",
  "公务员方向",
] as const;

export type TargetRole = (typeof TARGET_ROLES)[number];
