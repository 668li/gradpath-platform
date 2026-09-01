import type { ShareableSkills } from "@/types";
import type { DecisionEngineResponse } from "@/types/path-comparison";

/** 拉取公开技能分享数据；链接无效/已关闭返回 null */
export const fetchShareSkills = async (token: string): Promise<ShareableSkills | null> => {
  try {
    const res = await fetch(`/api/share/skills/${encodeURIComponent(token)}`);
    if (!res.ok) return null;
    return (await res.json()) as ShareableSkills;
  } catch {
    return null;
  }
};

/** 拉取公开报考决策报告；链接无效/已关闭返回 null（公开端点返回匿名化数据） */
export const fetchShareDecision = async (
  token: string,
): Promise<DecisionEngineResponse | null> => {
  try {
    const res = await fetch(`/api/share/decision/${encodeURIComponent(token)}`);
    if (!res.ok) return null;
    return (await res.json()) as DecisionEngineResponse;
  } catch {
    return null;
  }
};
