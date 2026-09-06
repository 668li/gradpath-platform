import { getToken } from "./client";

/**
 * 带鉴权的文件下载工具。
 * PDF/CSV 端点返回二进制流，不能用 request<T> 解析 JSON，
 * 需要 fetch + blob 直接下载。
 *
 * 微信内置浏览器拦截程序化下载（a[download] 失效），需要降级：
 * - PDF → 引导用户"右上角…在浏览器打开"后再导出
 * - CSV/JSON → 内容复制到剪贴板（HTTP 明文环境无 navigator.clipboard，退回 execCommand）
 * 返回值是给 toast 用的用户可读结果说明。
 */
const isWeChat = () =>
  typeof navigator !== "undefined" && /MicroMessenger/i.test(navigator.userAgent);

async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // 明文 HTTP 或权限拒绝，走 execCommand 兜底
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

async function downloadBlob(path: string, filename: string): Promise<string> {
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
  if (isWeChat()) {
    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("pdf") || filename.endsWith(".pdf")) {
      throw new Error(
        "微信内不支持下载文件：请点右上角「…」→「在浏览器打开」，回到本页再导出即可",
      );
    }
    const text = await resp.text();
    const ok = await copyText(text);
    if (!ok) {
      throw new Error("自动复制失败：请点右上角「…」→「在浏览器打开」后再导出");
    }
    return "内容已复制到剪贴板，可粘贴到备忘录/邮件保存";
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
  return "文件已开始下载";
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
    return downloadBlob(`/api/export-v2/school-report?${qs}`, filename);
  },

  /** 导出当前用户职业报告 PDF */
  careerReport: async () => downloadBlob("/api/export-v2/career-report", "career-report.pdf"),

  /** 导出当前用户个人报告 PDF */
  profileReport: async () => downloadBlob("/api/export-v2/profile-report", "profile-report.pdf"),

  /** 导出当前用户数据（CSV 或 JSON） */
  dataExport: async (format: "csv" | "json" = "json") => {
    const filename = format === "csv"
      ? "gradpath-data-export.csv"
      : "gradpath-data-export.json";
    return downloadBlob(`/api/export-v2/data-export?format=${format}`, filename);
  },
};
