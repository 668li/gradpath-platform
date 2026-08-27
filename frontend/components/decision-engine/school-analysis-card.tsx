"use client";

// frontend/components/decision-engine/school-analysis-card.tsx
// 考研院校级分析 — 命中院校的竞争档位 + 隐性情报（决策飞轮第一圈）

import { GraduationCap, Info } from "lucide-react";
import { Badge } from "@/components/ui/form-controls";
import type { SchoolAnalysis } from "@/types/path-comparison";

const COMPETITION_BADGE: Record<string, "red" | "slate" | "green"> = {
  偏高: "red",
  中等: "slate",
  偏低: "green",
};

export function SchoolAnalysisCard({ analysis }: { analysis: SchoolAnalysis }) {
  return (
    <section className="rounded-xl border border-blue-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white">
          <GraduationCap className="h-4 w-4" />
        </span>
        <div>
          <h3 className="text-base font-semibold text-ink-900">考研 · 院校级分析</h3>
          <p className="text-xs text-ink-500">{analysis.coverage_note}</p>
        </div>
      </div>

      <ul className="mt-4 space-y-2">
        {analysis.items.map((s) => (
          <li
            key={`${s.university_name}-${s.major_name}-${s.year ?? ""}`}
            className="rounded-lg border border-paper-100 bg-paper-50/60 p-3"
          >
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="text-sm font-medium text-ink-800">{s.university_name}</span>
              <span className="text-xs text-ink-500">{s.major_name}</span>
              {s.year && <span className="text-[11px] text-ink-400">{s.year} 年</span>}
              <Badge color={COMPETITION_BADGE[s.competition] ?? "slate"}>
                竞争{s.competition}
              </Badge>
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-ink-500">
              {s.score_line != null && <span>复试线 {s.score_line} 分</span>}
              {s.ratio && <span>报录比约 {s.ratio}</span>}
              {s.degree_type && <span>{s.degree_type}</span>}
            </div>
            {s.intel && (
              <div className="mt-1.5 flex items-start gap-1 rounded-md bg-indigo-50/70 px-2 py-1.5 text-[11px] leading-snug text-indigo-700">
                <Info className="mt-0.5 h-3 w-3 shrink-0" />
                {s.intel}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}