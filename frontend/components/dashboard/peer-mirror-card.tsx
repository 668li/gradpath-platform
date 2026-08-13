"use client";

import { Users, TrendingUp, Quote, Compass } from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/lib/api/swr-config";
import { peerInsightsApi } from "@/lib/api/peer-insights";
import type { PeerMirrorResponse } from "@/lib/api/peer-insights";

/** 去向类型 → 条形颜色 */
const DEST_BAR_COLORS: Record<string, string> = {
  postgrad: "bg-brand-500",
  employment: "bg-blue-500",
  civil_service: "bg-emerald-500",
  abroad: "bg-purple-500",
  phd: "bg-rose-500",
  startup: "bg-amber-500",
  gap_year: "bg-cyan-500",
};

/**
 * 同路人镜像 — 创意功能。
 * 把「和你同阶段的人怎么选、结果如何」用真实数据呈现，
 * 用社会证明对抗盲目焦虑与孤立决策。
 */
export function PeerMirrorCard() {
  const { data, isLoading } = useApi<PeerMirrorResponse>(
    "/api/peer-insights/mirror",
  );

  if (isLoading) {
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-32 rounded bg-paper-200 mb-4" />
        <div className="space-y-3">
          <div className="h-3 w-full rounded bg-paper-200" />
          <div className="h-3 w-3/4 rounded bg-paper-200" />
        </div>
      </div>
    );
  }

  if (!data || !data.has_data || data.distribution.length === 0) {
    return null;
  }

  const maxPercent = Math.max(...data.distribution.map((d) => d.percent), 1);

  return (
    <div className="card p-5 animate-fade-in">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-display font-semibold text-ink-800">
          <Users className="h-4 w-4 text-brand-600" />
          同路人镜像
        </h2>
        <span className="text-xs text-ink-400">
          基于 {data.peer_count} 位{data.stage_label}同路人
        </span>
      </div>

      {/* 去向分布条 */}
      <div className="space-y-2.5">
        {data.distribution.slice(0, 4).map((d) => (
          <div key={d.destination_type} className="flex items-center gap-3">
            <span className="w-12 shrink-0 text-xs text-ink-600">{d.label}</span>
            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-paper-100">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  DEST_BAR_COLORS[d.destination_type] || "bg-ink-400",
                )}
                style={{ width: `${(d.percent / maxPercent) * 100}%` }}
              />
            </div>
            <span className="w-10 shrink-0 text-right text-xs font-medium text-ink-700">
              {d.percent}%
            </span>
          </div>
        ))}
      </div>

      {/* 上岸率 */}
      {data.success_rate !== null && (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2.5">
          <TrendingUp className="h-4 w-4 shrink-0 text-brand-600" />
          <p className="text-sm text-brand-800">
            同路人公开上岸率{" "}
            <span className="font-bold">{data.success_rate}%</span>
          </p>
        </div>
      )}

      {/* 过来人真实建议 */}
      {data.peer_advice && (
        <div className="mt-3 rounded-lg border border-paper-200 bg-paper-50/50 p-3">
          <div className="flex items-start gap-2">
            <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-400" />
            <div className="min-w-0">
              <p className="text-xs leading-relaxed text-ink-600">
                {data.peer_advice.advice}
              </p>
              <p className="mt-1.5 text-[11px] text-ink-400">
                — {data.peer_advice.year} 届
                {data.peer_advice.target_school
                  ? ` · ${data.peer_advice.target_school}`
                  : ""}
                过来人
              </p>
            </div>
          </div>
        </div>
      )}

      <p className="mt-3 flex items-center gap-1 text-[11px] text-ink-400">
        <Compass className="h-3 w-3" />
        别人的选择是参考，不是答案 — 用决策实验室做出你自己的判断
      </p>
    </div>
  );
}
