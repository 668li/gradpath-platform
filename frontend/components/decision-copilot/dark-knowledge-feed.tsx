"use client";

import { memo, useState } from "react";
import { Bell, Check, ThumbsUp, ThumbsDown, Clock, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { darkKnowledgePushApi } from "@/lib/api";
import type { PulseDarkKnowledgeItem } from "@/types";

interface Props {
  items: PulseDarkKnowledgeItem[];
  loading?: boolean;
  onMarkRead?: (pushId: string) => void;
}

const IMPORTANCE_COLOR: Record<string, string> = {
  critical: "bg-red-50 text-red-700 border-red-200",
  high: "bg-amber-50 text-amber-700 border-amber-200",
  medium: "bg-blue-50 text-blue-700 border-blue-200",
  low: "bg-paper-100 text-ink-600 border-paper-200",
};

const IMPORTANCE_LABEL: Record<string, string> = {
  critical: "关键",
  high: "重要",
  medium: "中等",
  low: "一般",
};

/** 暗知识推送流 — 主动推送护城河 */
export const DarkKnowledgeFeedSection = memo(function DarkKnowledgeFeedSection({ items, loading, onMarkRead }: Props) {
  const toast = useToast();
  const [markingId, setMarkingId] = useState<string | null>(null);

  const handleMarkRead = async (pushId: string) => {
    setMarkingId(pushId);
    try {
      await darkKnowledgePushApi.markRead(pushId);
      onMarkRead?.(pushId);
    } catch {
      toast.error("标记失败");
    } finally {
      setMarkingId(null);
    }
  };

  const handleFeedback = async (pushId: string, feedback: "positive" | "negative") => {
    try {
      await darkKnowledgePushApi.feedback(pushId, { feedback });
      toast.success(feedback === "positive" ? "感谢反馈" : "已记录");
    } catch {
      toast.error("反馈失败");
    }
  };

  if (loading) return <LoadingState text="加载暗知识…" />;

  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-rose-600" />
          <h3 className="font-display font-semibold text-ink-800">暗知识推送</h3>
          {items.length > 0 && (
            <span className="rounded-full bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
              {items.filter((i) => !i.is_read).length} 未读
            </span>
          )}
        </div>
        <a
          href="/kaoyan/dark-knowledge"
          className="text-xs text-brand-600 hover:text-brand-700 inline-flex items-center"
        >
          暗知识库 <ArrowRight className="h-3 w-3" />
        </a>
      </div>

      {items.length === 0 ? (
        <EmptyState
          title="暂无暗知识推送"
          description="创建决策或定期检查时，平台会主动推送相关暗知识"
        />
      ) : (
        <ul className="space-y-2">
          {items.slice(0, 5).map((item) => (
            <li
              key={item.push_id}
              className={cn(
                "rounded-lg border p-3 transition-all",
                item.is_read
                  ? "border-paper-200 bg-white"
                  : "border-brand-200 bg-brand-50/40",
              )}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={cn(
                      "rounded-full border px-2 py-0.5 text-[10px] font-medium",
                      IMPORTANCE_COLOR[item.importance] ?? IMPORTANCE_COLOR.medium,
                    )}
                  >
                    {IMPORTANCE_LABEL[item.importance] ?? "中等"}
                  </span>
                  <p className="text-sm font-semibold text-ink-800 truncate">
                    {item.title}
                  </p>
                </div>
                {!item.is_read && (
                  <span className="h-2 w-2 rounded-full bg-brand-500 shrink-0 mt-1" />
                )}
              </div>
              <p className="text-xs text-ink-500 line-clamp-2 leading-relaxed">
                {item.content}
              </p>
              {item.actionable_advice && (
                <p className="mt-1.5 text-xs text-brand-700 bg-brand-50/60 px-2 py-1 rounded">
                  💡 {item.actionable_advice}
                </p>
              )}
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[10px] text-ink-400">
                  {item.pushed_at && new Date(item.pushed_at).toLocaleDateString("zh-CN")}
                </span>
                <div className="flex items-center gap-1">
                  {!item.is_read && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleMarkRead(item.push_id)}
                      loading={markingId === item.push_id}
                      className="!px-2 !py-0.5 !text-[10px]"
                    >
                      <Check className="h-3 w-3" />
                      标记已读
                    </Button>
                  )}
                  <button
                    onClick={() => handleFeedback(item.push_id, "positive")}
                    className="p-1 rounded hover:bg-emerald-50 text-ink-400 hover:text-emerald-600 transition-colors"
                    title="有用"
                  >
                    <ThumbsUp className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => handleFeedback(item.push_id, "negative")}
                    className="p-1 rounded hover:bg-red-50 text-ink-400 hover:text-red-600 transition-colors"
                    title="无用"
                  >
                    <ThumbsDown className="h-3 w-3" />
                  </button>
                  <button
                    onClick={() => handleFeedback(item.push_id, "negative")}
                    className="p-1 rounded hover:bg-paper-100 text-ink-400 transition-colors"
                    title="稍后看"
                  >
                    <Clock className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
});
