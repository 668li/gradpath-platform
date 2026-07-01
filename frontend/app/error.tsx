"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App error:", error);
  }, [error]);

  return (
    <div className="min-h-[400px] flex items-center justify-center p-8">
      <div className="max-w-md text-center space-y-4">
        <div className="flex justify-center">
          <AlertTriangle className="h-12 w-12 text-amber-500" />
        </div>
        <h2 className="text-xl font-semibold text-slate-800">页面出错了</h2>
        <p className="text-sm text-slate-500">
          抱歉，页面渲染时发生了错误。请尝试刷新或返回首页。
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <RotateCcw className="h-4 w-4" /> 重试
          </button>
          <a
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-100 text-slate-600 text-sm font-medium hover:bg-slate-200 transition-colors"
          >
            <Home className="h-4 w-4" /> 返回首页
          </a>
        </div>
      </div>
    </div>
  );
}
