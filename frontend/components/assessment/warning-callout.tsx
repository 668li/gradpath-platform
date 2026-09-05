"use client";

import { AlertTriangle } from "lucide-react";

/**
 * 信度/完整性警示卡：把后端折进 result_summary 的【作答提示】逐条亮出来，
 * 放在推荐职业方向之前——先看警示，再看方向，诚实降级才有牙。
 */
export function WarningCallout({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <div
      className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-4"
      data-testid="answer-warning-callout"
    >
      <div className="flex items-center gap-2 text-sm font-medium text-amber-800 mb-1.5">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        作答提示
      </div>
      <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
        {warnings.map((w, i) => (
          <li key={`warn-${i}`}>{w}</li>
        ))}
      </ul>
    </div>
  );
}
