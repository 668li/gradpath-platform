"use client";

import Link from "next/link";
import {
  ArrowRight,
  Lightbulb,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { PulseDarkKnowledgeItem } from "@/types";

// ===== 暗知识推送卡片 =====

/** 暗知识重要性 → 配色 */
const DK_IMPORTANCE_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-yellow-100 text-yellow-700",
};

const DK_IMPORTANCE_LABEL: Record<string, string> = {
  critical: "关键",
  high: "重要",
  medium: "中等",
  low: "一般",
};

/** 暗知识推送卡片：突出显示用户可能不知道但重要的信息 */
export function DarkKnowledgeCard({
  item,
  onMarkRead,
}: {
  item: PulseDarkKnowledgeItem | null;
  onMarkRead: (pushId: string) => void;
}) {
  return (
    <section className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-4 animate-fade-in">
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
          <Lightbulb className="h-4 w-4" />
        </div>
        <h2 className="font-display font-semibold text-ink-800">暗知识推送</h2>
        <span className="text-xs text-ink-400">你不知道但可能重要的信息</span>
      </div>

      {item ? (
        <div className="space-y-3">
          <div className="flex items-start gap-2">
            {item.importance && (
              <span
                className={cn(
                  "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium",
                  DK_IMPORTANCE_COLOR[item.importance] ?? DK_IMPORTANCE_COLOR.medium,
                )}
              >
                {DK_IMPORTANCE_LABEL[item.importance] ?? "中等"}
              </span>
            )}
            {item.category && (
              <span className="shrink-0 text-xs text-ink-400">{item.category}</span>
            )}
          </div>
          <div>
            <p className="text-sm font-semibold text-ink-800">{item.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-ink-600 line-clamp-3">
              {item.content}
            </p>
          </div>
          <p className="text-xs text-amber-700 italic">
            这可能是你不知道但重要的信息
          </p>
          {item.actionable_advice && (
            <div className="rounded-lg bg-white/60 px-3 py-2">
              <p className="text-xs text-ink-600">
                <span className="font-medium text-amber-700">建议行动：</span>
                {item.actionable_advice}
              </p>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Link
              href="/kaoyan/dark-knowledge"
              className="inline-flex items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 transition-colors"
            >
              查看详情 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <button
              onClick={() => onMarkRead(item.push_id)}
              className="inline-flex items-center gap-1 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-50 transition-colors"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              已了解
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 py-3 text-sm text-ink-500">
          <Sparkles className="h-4 w-4 text-amber-500" />
          <span>暂无新发现，继续探索会有新洞察</span>
        </div>
      )}
    </section>
  );
}
