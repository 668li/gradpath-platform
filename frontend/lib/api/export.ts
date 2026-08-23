import type { ShareableSkills } from "@/types";

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
