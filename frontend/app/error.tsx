"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RotateCcw, Home, Trash2 } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App error:", error);
    // 自动重试 1 次（延迟 2 秒）
    const timer = setTimeout(() => {
      reset();
    }, 2000);
    return () => clearTimeout(timer);
  }, [error]);

  const handleClearCache = () => {
    try {
      localStorage.removeItem("gradpath_access_token");
      localStorage.removeItem("gradpath_refresh_token");
      document.cookie = "gradpath_token=; Path=/; SameSite=Lax; Max-Age=0";
    } catch {
      // 忽略 localStorage 不可用的情况
    }
    window.location.reload();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-100 px-4">
      <div className="card max-w-md w-full text-center space-y-4">
        <div className="flex justify-center">
          <AlertTriangle className="h-12 w-12 text-amber-500" />
        </div>
        <h2 className="text-xl font-semibold text-ink-800">页面渲染遇到问题</h2>
        <p className="text-sm text-ink-500">
          系统正在自动重试。如果问题持续，请尝试以下操作：
        </p>
        {error.message && (
          <p className="text-xs text-ink-400 bg-ink-50 rounded p-2 font-mono break-all">
            {error.message.slice(0, 100)}
          </p>
        )}
        <div className="flex flex-col gap-2 pt-2">
          <button
            onClick={() => reset()}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <RotateCcw className="h-4 w-4" /> 重新加载
          </button>
          <button
            onClick={handleClearCache}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-ink-100 text-ink-600 text-sm font-medium hover:bg-ink-200 transition-colors"
          >
            <Trash2 className="h-4 w-4" /> 清除缓存并刷新
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-transparent text-ink-600 text-sm font-medium hover:bg-ink-100 transition-colors"
          >
            <Home className="h-4 w-4" /> 返回首页
          </Link>
        </div>
      </div>
    </div>
  );
}
