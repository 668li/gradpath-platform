"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Download, FileJson, FileText, Loader2 } from "lucide-react";
import { getToken } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

/**
 * 导出按钮 — 下拉菜单提供 PDF 时间线与 JSON 备份两种导出方式。
 *
 * 因为 PDF/JSON 接口需要鉴权，不能直接用 window.open（无法带 Authorization 头），
 * 所以用 fetch + blob 的方式下载。
 */
export function ExportButton() {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState<"pdf" | "json" | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
    return;
  }, [open]);

  /** 通用：带鉴权头请求接口并触发浏览器下载 */
  async function downloadBlob(
    path: string,
    filename: string,
    kind: "pdf" | "json",
  ) {
    const token = getToken();
    if (!token) {
      toast.push("请先登录后再导出", "error");
      return;
    }
    setLoading(kind);
    try {
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
      // 释放 object URL，避免内存泄漏
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.push(`${kind === "pdf" ? "PDF" : "JSON"} 导出成功`, "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "导出失败", "error");
    } finally {
      setLoading(null);
      setOpen(false);
    }
  }

  const handlePdf = () =>
    downloadBlob("/api/export/timeline.pdf", "gradpath-timeline.pdf", "pdf");
  const handleJson = () =>
    downloadBlob("/api/export/profile.json", "gradpath-profile.json", "json");

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={loading !== null}
        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Download className="h-4 w-4" />
        )}
        导出
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-1 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
          <button
            type="button"
            onClick={handlePdf}
            disabled={loading !== null}
            className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FileText className="h-4 w-4 text-red-500" />
            <span>导出 PDF 时间线</span>
          </button>
          <button
            type="button"
            onClick={handleJson}
            disabled={loading !== null}
            className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <FileJson className="h-4 w-4 text-amber-500" />
            <span>导出 JSON 备份</span>
          </button>
        </div>
      )}
    </div>
  );
}
