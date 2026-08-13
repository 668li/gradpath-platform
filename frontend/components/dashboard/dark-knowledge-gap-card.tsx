"use client";

import { useState } from "react";
import Link from "next/link";
import { Radar, Eye, ChevronDown, ArrowRight, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api/swr-config";
import { peerInsightsApi } from "@/lib/api/peer-insights";
import type { DarkKnowledgeGapResponse } from "@/lib/api/peer-insights";

/** 暗知识阶段 → 中文标签 */
const STAGE_LABELS: Record<string, string> = {
  decision: "决策期",
  school_selection: "择校期",
  preparation: "备考期",
  exam: "考试期",
  retest: "复试期",
  transfer: "调剂期",
};

/**
 * 暗知识缺口雷达 — 创意功能。
 * 主动浮出"你还没看到、但同路人都在看"的高重要性暗知识，
 * 用"别人都看了 N 人"制造社会证明，对抗"你不知道你不知道"。
 */
export function DarkKnowledgeGapCard() {
  const { data, isLoading } = useApi<DarkKnowledgeGapResponse>(
    "/api/peer-insights/dark-knowledge-gap",
  );
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-36 rounded bg-paper-200 mb-4" />
        <div className="space-y-3">
          <div className="h-3 w-full rounded bg-paper-200" />
          <div className="h-3 w-5/6 rounded bg-paper-200" />
        </div>
      </div>
    );
  }

  if (!data || !data.has_gap) {
    return null;
  }

  return (
    <div className="card p-5 animate-fade-in">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-display font-semibold text-ink-800">
          <Radar className="h-4 w-4 text-purple-500" />
          暗知识缺口雷达
        </h2>
        <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-600">
          {data.gap_count} 条待解锁
        </span>
      </div>
      <p className="mb-4 text-xs text-ink-400">
        这些关键信息你还没看过，但很多同路人已经看了
      </p>

      <div className="space-y-2">
        {data.items.map((item) => {
          const isExpanded = expandedId === item.id;
          return (
            <div
              key={item.id}
              className="rounded-lg border border-paper-200 transition-all hover:border-purple-200"
            >
              <button
                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
              >
                <Lightbulb className="h-4 w-4 shrink-0 text-purple-500" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink-700">
                    {item.title}
                  </p>
                  <p className="mt-0.5 flex items-center gap-1 text-[11px] text-ink-400">
                    <Eye className="h-3 w-3" />
                    {item.read_by_peers > 0
                      ? `${item.read_by_peers} 位同路人已读`
                      : "新暗知识"}
                    {item.stage && (
                      <span className="ml-1 rounded bg-paper-100 px-1.5 py-0.5">
                        {STAGE_LABELS[item.stage] || item.stage}
                      </span>
                    )}
                  </p>
                </div>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 text-ink-400 transition-transform",
                    isExpanded && "rotate-180",
                  )}
                />
              </button>

              {isExpanded && (
                <div className="border-t border-paper-100 px-3 py-3">
                  <p className="text-sm leading-relaxed text-ink-600">
                    {item.content_preview}
                    {item.content_preview.length >= 120 && "…"}
                  </p>
                  {item.common_misconception && (
                    <p className="mt-2 rounded bg-amber-50 px-2 py-1.5 text-xs text-amber-700">
                      常见误区：{item.common_misconception}
                    </p>
                  )}
                  <Link
                    href="/kaoyan/dark-knowledge"
                    className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
                  >
                    查看完整暗知识库
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
