"use client";

import { memo } from "react";
import { cn } from "@/lib/utils";

interface SchoolComparisonRow {
  university_name: string;
  latest_year: number | null;
  latest_scoreline: number | null;
  program_count: number;
  adjustment_count: number;
}

interface SchoolComparisonTableProps {
  schools: SchoolComparisonRow[];
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-ink-400">—</span>;

  let color = "text-green-700 bg-green-50";
  if (score >= 400) color = "text-red-700 bg-red-50";
  else if (score >= 370) color = "text-amber-700 bg-amber-50";
  else if (score >= 340) color = "text-blue-700 bg-blue-50";

  return (
    <span className={cn("inline-block px-2 py-0.5 rounded-full text-xs font-medium", color)}>
      {score}
    </span>
  );
}

export const SchoolComparisonTable = memo(function SchoolComparisonTable({ schools }: SchoolComparisonTableProps) {
  if (!schools.length) {
    return (
      <div className="flex items-center justify-center text-sm text-ink-400 py-8">
        请选择至少一所院校进行对比
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-paper-200 text-left text-xs text-ink-500">
            <th className="px-3 py-2 font-medium">院校</th>
            <th className="px-3 py-2 font-medium">最新年份</th>
            <th className="px-3 py-2 font-medium text-center">复试线</th>
            <th className="px-3 py-2 font-medium text-center">专业数</th>
            <th className="px-3 py-2 font-medium text-center">调剂数</th>
            <th className="px-3 py-2 font-medium text-center">综合评估</th>
          </tr>
        </thead>
        <tbody>
          {schools.map((s) => {
            const score = s.latest_scoreline;
            let tier = "保底";
            let tierColor = "text-green-700 bg-green-50";
            if (score !== null) {
              if (score >= 380) {
                tier = "冲刺";
                tierColor = "text-red-700 bg-red-50";
              } else if (score >= 350) {
                tier = "稳妥";
                tierColor = "text-amber-700 bg-amber-50";
              }
            }

            return (
              <tr
                key={s.university_name}
                className="border-b border-paper-100 hover:bg-paper-50/50"
              >
                <td className="px-3 py-3 font-medium text-ink-800">
                  {s.university_name}
                </td>
                <td className="px-3 py-3 text-ink-500">
                  {s.latest_year ?? "—"}
                </td>
                <td className="px-3 py-3 text-center">
                  <ScoreBadge score={s.latest_scoreline} />
                </td>
                <td className="px-3 py-3 text-center text-ink-600">
                  {s.program_count}
                </td>
                <td className="px-3 py-3 text-center text-ink-600">
                  {s.adjustment_count}
                </td>
                <td className="px-3 py-3 text-center">
                  <span
                    className={cn(
                      "inline-block px-2 py-0.5 rounded-full text-xs font-medium",
                      tierColor,
                    )}
                  >
                    {tier}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
});
