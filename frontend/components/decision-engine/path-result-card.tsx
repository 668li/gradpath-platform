"use client";

// frontend/components/decision-engine/path-result-card.tsx
// 单路结果卡片 — 核心数字 + 证据溯源展开（source_url 可点击）

import {
  GraduationCap, Briefcase, Landmark, ShieldAlert, TrendingUp,
  Clock, ExternalLink, FileSearch,
} from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
import { cn } from "@/lib/utils";
import type { PathMetrics, RiskLevel } from "@/types/path-comparison";

// 三路元信息（与后端 PATH_LABELS / 前端 path-comparison-table 对齐）
const PATH_META: Record<
  string,
  { label: string; icon: React.ReactNode; gradient: string; accent: string }
> = {
  kaoyan: {
    label: "考研深造",
    icon: <GraduationCap className="h-4 w-4" />,
    gradient: "from-blue-500 to-indigo-600",
    accent: "text-blue-600 bg-blue-50 border-blue-200",
  },
  civil_service: {
    label: "考公",
    icon: <Landmark className="h-4 w-4" />,
    gradient: "from-amber-500 to-orange-600",
    accent: "text-amber-600 bg-amber-50 border-amber-200",
  },
  employment: {
    label: "直接就业",
    icon: <Briefcase className="h-4 w-4" />,
    gradient: "from-emerald-500 to-teal-600",
    accent: "text-emerald-600 bg-emerald-50 border-emerald-200",
  },
};

const RISK_META: Record<RiskLevel, { label: string; className: string }> = {
  low: { label: "低风险", className: "bg-green-100 text-green-700 border-green-200" },
  medium: { label: "中风险", className: "bg-amber-100 text-amber-700 border-amber-200" },
  high: { label: "高风险", className: "bg-red-100 text-red-700 border-red-200" },
};

/** 把证据 label 映射为展示图标分组（分数线/岗位/行业数据/院校/其他） */
function evidenceIcon(label: string): React.ReactNode {
  if (label.includes("分数线") || label.includes("报录") || label.includes("招生")) {
    return <GraduationCap className="h-3.5 w-3.5" />;
  }
  if (label.includes("岗位")) {
    return <Landmark className="h-3.5 w-3.5" />;
  }
  if (label.includes("行业") || label.includes("薪资")) {
    return <Briefcase className="h-3.5 w-3.5" />;
  }
  if (label.includes("院校")) {
    return <TrendingUp className="h-3.5 w-3.5" />;
  }
  return <FileSearch className="h-3.5 w-3.5" />;
}

export function PathResultCard({ metric }: { metric: PathMetrics }) {
  const meta = PATH_META[metric.path_type] ?? {
    label: metric.target_role,
    icon: <FileSearch className="h-4 w-4" />,
    gradient: "from-ink-400 to-ink-500",
    accent: "text-ink-600 bg-ink-50 border-ink-200",
  };
  const risk = RISK_META[metric.risk_level] ?? RISK_META.medium;
  const evidence = metric.evidence ?? [];
  const noData = metric.match_score === 0;

  return (
    <div className="flex flex-col rounded-xl border border-paper-200 bg-white p-5 shadow-sm">
      {/* 头部：路径名 + 风险 Badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={cn(
            "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-white",
            meta.gradient,
          )}>
            {meta.icon}
          </span>
          <div>
            <div className="font-semibold text-ink-900">{meta.label}</div>
            <div className="text-xs text-ink-400">{metric.target_role}</div>
          </div>
        </div>
        <span className={cn(
          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
          risk.className,
        )}>
          <ShieldAlert className="h-3 w-3" />
          {risk.label}
        </span>
      </div>

      {/* 核心数字 */}
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg bg-paper-50 p-3">
          <div className="text-xs text-ink-400">数据覆盖度</div>
          <div className={cn("mt-0.5 text-lg font-bold", noData ? "text-ink-400" : "text-ink-900")}>
            {metric.match_score}{metric.match_score > 0 && <span className="text-xs font-normal text-ink-400">/100</span>}
          </div>
          {metric.match_description && !noData && (
            <div className="mt-0.5 text-[11px] leading-snug text-ink-400">{metric.match_description}</div>
          )}
        </div>
        <div className="rounded-lg bg-paper-50 p-3">
          <div className="text-xs text-ink-400">成长性</div>
          <div className="mt-0.5 flex items-center gap-2">
            <div className="h-1.5 w-14 overflow-hidden rounded-full bg-ink-100">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500"
                style={{ width: `${(metric.growth_score / 10) * 100}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-ink-700">{metric.growth_score}/10</span>
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-1 text-xs text-ink-400">
        <Clock className="h-3 w-3" />
        准备/过渡期约 {metric.time_cost_months} 个月
      </div>

      {/* 风险说明 */}
      <p className="mt-2 text-xs leading-relaxed whitespace-pre-line text-ink-500">
        {metric.risk_description}
      </p>

      {/* 要点（pros/cons） */}
      {metric.pros.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-ink-600">
          {metric.pros.map((p, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="mt-0.5 text-green-500">✓</span>
              <span className="leading-snug">{p}</span>
            </li>
          ))}
        </ul>
      )}
      {metric.cons.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-ink-500">
          {metric.cons.map((c, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="mt-0.5 text-amber-500">!</span>
              <span className="leading-snug">{c}</span>
            </li>
          ))}
        </ul>
      )}

      {/* 证据溯源展开 */}
      {evidence.length > 0 && (
        <details className="mt-4 group">
          <summary className={cn(
            "flex cursor-pointer select-none items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors",
            meta.accent,
          )}>
            <FileSearch className="h-3.5 w-3.5" />
            溯源 · 共 {evidence.length} 条证据
            <span className="ml-auto text-[10px] opacity-70 group-open:rotate-180 transition-transform">▾</span>
          </summary>
          <ul className="mt-2 space-y-1.5">
            {evidence.map((ev, i) => (
              <li key={i} className="rounded-lg border border-paper-100 bg-paper-50/60 p-2.5">
                <div className="flex items-center gap-1.5 text-[11px] font-medium text-ink-600">
                  <span className="text-ink-400">{evidenceIcon(ev.label)}</span>
                  <span>{ev.label}</span>
                </div>
                <div className="mt-0.5 pl-5 text-[11px] leading-snug text-ink-500">{ev.value}</div>
                {(ev.source_url || ev.note) && (
                  <div className="mt-1 pl-5">
                    {ev.source_url ? (
                      <a
                        href={ev.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] text-brand-600 hover:underline"
                      >
                        查看来源 <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-[11px] text-ink-400">{ev.note}</span>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* 空数据标识 */}
      {noData && (
        <div className="mt-3 rounded-lg border border-dashed border-ink-200 bg-paper-50 p-3 text-center">
          <Badge color="slate">数据有限</Badge>
          <p className="mt-1.5 text-xs leading-snug text-ink-500">{metric.match_description}</p>
        </div>
      )}
    </div>
  );
}
