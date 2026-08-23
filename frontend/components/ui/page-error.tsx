"use client";

import { useEffect } from "react";
import { EmptyState } from "@/components/ui/empty";

interface PageErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
  label: string;
}

/**
 * 分段路由错误边界（error.tsx 共享实现）。
 * 仅差异在 console.error 的页面标识 label，渲染与交互完全一致：
 * 显示 EmptyState + 重试/返回首页按钮。
 */
export function PageError({ error, reset, label }: PageErrorProps) {
  useEffect(() => {
    console.error(`${label} 页面错误:`, error);
  }, [error, label]);

  return (
    <EmptyState
      title="页面加载失败"
      description="发生了一些问题，可以重试或返回首页"
      action={
        <div className="flex gap-2">
          <button
            onClick={reset}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
          >
            重试
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 border rounded-lg hover:bg-ink-50 transition-colors"
          >
            返回首页
          </a>
        </div>
      }
    />
  );
}
