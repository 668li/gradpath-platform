"use client";

// frontend/components/decision-engine/position-analysis-card.tsx
// 考公岗位级分析 — 基于个人条件的可报清单 + 进面线分布 + 竞争力分级（决策飞轮第一圈）

import { Landmark, MapPin, Target, Users } from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
import type { PositionAnalysis } from "@/types/path-comparison";

const LEVEL_BADGE_COLOR: Record<string, "green" | "blue" | "amber" | "slate"> = {
  稳健: "green",
  均衡: "blue",
  冲刺: "amber",
};

/** 竞争力分级说明（条件式结论，不替用户决定） */
const LEVEL_DESC: Record<string, string> = {
  稳健: "多数可报岗位的进面线明显低于你的预估分，上岸概率相对更高",
  均衡: "可报岗位进面线与你的预估分大致相当，属于需要认真发挥的区间",
  冲刺: "多数可报岗位进面线高于你的预估分，需要超常发挥或调整目标",
};

export function PositionAnalysisCard({ analysis }: { analysis: PositionAnalysis }) {
  const badgeColor = LEVEL_BADGE_COLOR[analysis.personalized_level ?? ""] ?? "slate";
  return (
    <section className="rounded-xl border border-amber-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 text-white">
            <Landmark className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-base font-semibold text-ink-900">考公 · 岗位级分析</h3>
            <p className="text-xs text-ink-500">按你的个人条件过滤后的可报岗位与进面线分层</p>
          </div>
        </div>
        {analysis.personalized_level && (
          <Badge color={badgeColor}>
            <Target className="mr-1 h-3 w-3" />
            个人竞争力：{analysis.personalized_level}
          </Badge>
        )}
      </div>

      {/* 关键数字 */}
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
        <div className="rounded-lg bg-paper-50 p-3">
          <div className="flex items-center gap-1 text-xs text-ink-400">
            <Landmark className="h-3 w-3" /> 国考可报
          </div>
          <div className="mt-0.5 text-lg font-bold text-ink-900">
            {analysis.eligible_count} 个
          </div>
          <div className="text-[11px] text-ink-400">按职位去重</div>
        </div>
        <div className="rounded-lg bg-paper-50 p-3">
          <div className="flex items-center gap-1 text-xs text-ink-400">
            <Users className="h-3 w-3" /> 省考可报
          </div>
          <div className="mt-0.5 text-lg font-bold text-ink-900">
            {analysis.province_count} 个
          </div>
          <div className="text-[11px] text-ink-400">按官方字段过滤</div>
        </div>
        <div className="rounded-lg bg-paper-50 p-3 md:col-span-1 col-span-2">
          <div className="text-xs text-ink-400">进面线分布</div>
          <div className="mt-0.5 text-sm font-semibold leading-snug text-ink-800">
            {analysis.score_band}
          </div>
        </div>
      </div>

      {/* 分级摘要 */}
      {analysis.tier_summary && (
        <p className="mt-3 rounded-lg border border-amber-100 bg-amber-50/60 px-3 py-2 text-xs leading-relaxed text-ink-600">
          {analysis.tier_summary}
          {analysis.personalized_level && (
            <span className="block text-ink-500">{LEVEL_DESC[analysis.personalized_level]}</span>
          )}
        </p>
      )}

      {/* 示例岗位 */}
      {analysis.top_positions.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-xs font-medium text-ink-600">可报岗位示例（招录人数优先）</div>
          <ul className="space-y-2">
            {analysis.top_positions.map((p, i) => (
              <li
                key={`${p.dept_name}-${p.position_name}-${i}`}
                className="rounded-lg border border-paper-100 bg-paper-50/60 p-3"
              >
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-sm font-medium text-ink-800">{p.dept_name}</span>
                  <span className="text-xs text-ink-500">{p.position_name}</span>
                  {p.work_location && (
                    <span className="inline-flex items-center gap-0.5 text-[11px] text-ink-400">
                      <MapPin className="h-3 w-3" /> {p.work_location}
                    </span>
                  )}
                  {p.recruit_count != null && (
                    <span className="text-[11px] text-ink-400">招 {p.recruit_count} 人</span>
                  )}
                </div>
                <div className="mt-1 text-[11px] text-ink-500">{p.score_label}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 数据诚实标注 */}
      {analysis.notes.length > 0 && (
        <ul className="mt-3 space-y-0.5 text-[11px] text-ink-400">
          {analysis.notes.map((n, i) => (
            <li key={i}>· {n}</li>
          ))}
        </ul>
      )}
    </section>
  );
}