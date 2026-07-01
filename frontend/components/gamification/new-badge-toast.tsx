"use client";

import { useEffect } from "react";
import { X, Sparkles } from "lucide-react";
import type { Badge } from "@/types";

interface NewBadgeToastProps {
  badges: Badge[];
  onDismiss: () => void;
}

/**
 * 新徽章获得提示：右上角固定定位，5 秒后自动消失。
 * 当 badges 非空时显示，每枚徽章渲染一条通知。
 */
export function NewBadgeToast({ badges, onDismiss }: NewBadgeToastProps) {
  useEffect(() => {
    if (badges.length === 0) return;
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [badges, onDismiss]);

  if (badges.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex w-80 max-w-[90vw] flex-col gap-2">
      {badges.map((badge) => (
        <div
          key={badge.code}
          className="flex items-start gap-3 rounded-lg border border-brand-200 bg-white px-4 py-3 shadow-lg"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600">
            <Sparkles className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-brand-700">
              恭喜获得新徽章！
            </p>
            <p className="truncate text-sm text-slate-700">{badge.name}</p>
          </div>
          <button
            onClick={onDismiss}
            className="shrink-0 text-slate-400 hover:text-slate-600"
            aria-label="关闭"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
