"use client";

import { useEffect } from "react";
import { EmptyState } from "@/components/ui/empty";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard 页面错误:", error);
  }, [error]);

  return (
    <EmptyState
      title="页面加载失败"
      description="发生了一些问题，可以重试或返回首页"
      action={
        <div className="flex gap-2">
          <button
            onClick={reset}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            重试
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 border rounded-lg hover:bg-slate-50 transition-colors"
          >
            返回首页
          </a>
        </div>
      }
    />
  );
}
