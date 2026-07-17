import type { ShareableSkills } from "@/types";

// ===== 导出 =====
export const exportApi = {
  /** PDF 时间线下载地址（需带 Authorization 头，由组件侧 fetch + blob） */
  timelinePdf: () => "/api/export/timeline.pdf",
  /** JSON 备份下载地址（需带 Authorization 头，由组件侧 fetch + blob） */
  profileJson: () => "/api/export/profile.json",
  /** 考研情报 PDF 下载地址 */
  gradIntelPdf: () => "/api/export/grad-intel/pdf",
  /** 考研情报 CSV 下载地址 */
  gradIntelCsv: () => "/api/export/grad-intel/csv",
  /** 考研情报 JSON 下载地址 */
  gradIntelJson: () => "/api/export/grad-intel",
  /** 暗知识按阶段 PDF 下载地址 */
  darkKnowledgePdf: (stage?: string) =>
    `/api/export/dark-knowledge/pdf${stage ? `?stage=${encodeURIComponent(stage)}` : ""}`,
  /** 公开技能分享地址（无需鉴权） */
  shareSkills: (token: string) => `/api/share/skills/${token}`,
  /** 拉取公开技能分享数据；链接无效/已关闭返回 null */
  fetchShareSkills: async (token: string): Promise<ShareableSkills | null> => {
    try {
      const res = await fetch(exportApi.shareSkills(token));
      if (!res.ok) return null;
      return (await res.json()) as ShareableSkills;
    } catch {
      return null;
    }
  },
};