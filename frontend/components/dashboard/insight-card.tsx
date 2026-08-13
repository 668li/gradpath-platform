"use client";

import {
  ArrowRight,
  Search,
  Bell,
  PartyPopper,
  AlertTriangle,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProactiveInsight } from "@/types";

// ===== AI 主动洞察：辅助函数 =====

/** 洞察类型对应图标 */
function getInsightIcon(type: ProactiveInsight["insight_type"]) {
  switch (type) {
    case "pattern":
      return <Search className="h-4 w-4" />;
    case "reminder":
      return <Bell className="h-4 w-4" />;
    case "celebration":
      return <PartyPopper className="h-4 w-4" />;
    case "warning":
      return <AlertTriangle className="h-4 w-4" />;
    case "suggestion":
      return <Lightbulb className="h-4 w-4" />;
    default:
      return <Sparkles className="h-4 w-4" />;
  }
}

/** 洞察类型对应的图标背景配色 */
function getInsightIconBg(type: ProactiveInsight["insight_type"]) {
  switch (type) {
    case "pattern":
      return "bg-blue-50 text-blue-600";
    case "reminder":
      return "bg-amber-50 text-amber-600";
    case "celebration":
      return "bg-green-50 text-green-600";
    case "warning":
      return "bg-red-50 text-red-600";
    case "suggestion":
      return "bg-brand-50 text-brand-600";
    default:
      return "bg-paper-100 text-ink-500";
  }
}

/** 优先级对应的左侧色条：5=红 4=琥珀 3=品牌 2=蓝 1=灰 */
function getPriorityBorder(priority: number) {
  switch (priority) {
    case 5:
      return "border-l-red-500";
    case 4:
      return "border-l-amber-500";
    case 3:
      return "border-l-brand-500";
    case 2:
      return "border-l-blue-500";
    default:
      return "border-l-ink-300";
  }
}

/** 单条 AI 洞察卡片：点击标记已读，未读有品牌色底，按优先级显示左色条 */
export function InsightCard({
  insight,
  onRead,
}: {
  insight: ProactiveInsight;
  onRead: (id: string) => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => !insight.is_read && onRead(insight.id)}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !insight.is_read) {
          e.preventDefault();
          onRead(insight.id);
        }
      }}
      className={cn(
        "group cursor-pointer rounded-xl border border-l-4 border-paper-200 px-4 py-3 transition-all hover:border-paper-300 hover:shadow-card-hover",
        getPriorityBorder(insight.priority),
        insight.is_read ? "bg-white" : "bg-brand-50/60",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
            getInsightIconBg(insight.insight_type),
          )}
        >
          {getInsightIcon(insight.insight_type)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-ink-800">
              {insight.title}
            </p>
            {!insight.is_read && (
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
            )}
          </div>
          <p className="mt-0.5 text-xs leading-relaxed text-ink-500">
            {insight.content}
          </p>
          {insight.action_suggestion && (
            <p className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-600 group-hover:underline">
              {insight.action_suggestion}
              <ArrowRight className="h-3 w-3" />
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
