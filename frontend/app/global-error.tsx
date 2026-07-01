"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="min-h-screen flex items-center justify-center p-8">
          <div className="max-w-md text-center space-y-4">
            <div className="flex justify-center">
              <AlertTriangle className="h-12 w-12 text-amber-500" />
            </div>
            <h2 className="text-xl font-semibold text-slate-800">应用发生严重错误</h2>
            <p className="text-sm text-slate-500">
              请尝试刷新页面。如果问题持续，请联系管理员。
            </p>
            <button
              onClick={reset}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700"
            >
              <RotateCcw className="h-4 w-4" /> 重试
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
