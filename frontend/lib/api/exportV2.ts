import { getToken } from "./client";

/**
 * 带鉴权的文件下载工具。
 * PDF/CSV 端点返回二进制流，不能用 request<T> 解析 JSON，
 * 需要 fetch + blob 直接下载。
 */
async function downloadBlob(
  path: string,
  filename: string,
): Promise<void> {
  const token = getToken();
  if (!token) {
    throw new Error("请先登录后再导出");
  }
  const resp = await fetch(path, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    const text = await resp.text();
    let msg = `导出失败 (${resp.status})`;
    try {
      const data = text ? JSON.parse(text) : null;
      if (data?.detail) msg = typeof data.detail === "string" ? data.detail : msg;
    } catch {
      // 非 JSON 错误体，忽略
    }
    throw new Error(msg);
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const exportV2Api = {
  /** 导出院校报告 PDF（需 school_id 或 school_name） */
  schoolReport: async (params: { schoolId?: string; schoolName?: string }) => {
    const { schoolId, schoolName } = params;
    const sp = new URLSearchParams();
    if (schoolId) sp.append("school_id", schoolId);
    if (schoolName) sp.append("school_name", schoolName);
    const qs = sp.toString();
    const filename = `school-report-${schoolName || schoolId || "unknown"}.pdf`.replace(/\s+/g, "-");
    await downloadBlob(`/api/export-v2/school-report?${qs}`, filename);
  },

  /** 导出当前用户职业报告 PDF */
  careerReport: async () => {
    await downloadBlob("/api/export-v2/career-report", "career-report.pdf");
  },

  /** 导出当前用户个人报告 PDF */
  profileReport: async () => {
    await downloadBlob("/api/export-v2/profile-report", "profile-report.pdf");
  },

  /** 导出当前用户数据（CSV 或 JSON） */
  dataExport: async (format: "csv" | "json" = "json") => {
    const filename = format === "csv"
      ? "gradpath-data-export.csv"
      : "gradpath-data-export.json";
    await downloadBlob(`/api/export-v2/data-export?format=${format}`, filename);
  },
};
