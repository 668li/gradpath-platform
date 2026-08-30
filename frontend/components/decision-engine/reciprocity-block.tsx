"use client";

// frontend/components/decision-engine/reciprocity-block.tsx
// 互惠回传块 — 回传闭环的信任底座：展示全站真实回传量（哪怕为 0 也如实说），
// 把"回传"从道德号召变成互惠契约（你的结果换下一届的精度）。

import { useEffect, useState } from "react";
import { HeartHandshake } from "lucide-react";
import { pathDecisionApi } from "@/lib/api";
import type { OutcomeStats } from "@/types/path-comparison";

const PATH_LABELS: Record<string, string> = {
  kaoyan: "考研",
  civil_service: "考公",
  employment: "就业",
};

const STATUS_LABELS: Record<string, string> = {
  achieved: "已上岸",
  following: "在备考路上",
  pending: "待出结果",
  abandoned: "放弃了该选择",
};

export function ReciprocityBlock() {
  const [stats, setStats] = useState<OutcomeStats | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    pathDecisionApi
      .getOutcomeStats()
      .then(setStats)
      .catch(() => setFailed(true));
  }, []);

  if (failed || !stats) return null;

  const n = stats.total_outcomes;

  // 分布简述：只列数量真实存在的维度，绝不凑数
  const parts: string[] = [];
  for (const [status, count] of Object.entries(stats.by_status)) {
    if (count > 0 && STATUS_LABELS[status]) {
      parts.push(`${STATUS_LABELS[status]} ${count} 人`);
    }
  }
  const pathParts: string[] = [];
  for (const [path, count] of Object.entries(stats.by_selected_path)) {
    if (count > 0 && PATH_LABELS[path]) {
      pathParts.push(`${PATH_LABELS[path]} ${count} 条`);
    }
  }

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 px-4 py-3">
      <div className="flex items-start gap-3">
        <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-white">
          <HeartHandshake className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1 text-xs leading-relaxed text-ink-600">
          {n > 0 ? (
            <>
              <span className="font-semibold text-ink-800">
                这套算法的准，靠 {n} 条真实结果支撑
              </span>
              （{[...parts, ...pathParts].join(" · ") || "详见下方"}）。你今天看到的每个判定，
              都是有人愿意交回自己真实结局的结果。
            </>
          ) : (
            <>
              <span className="font-semibold text-ink-800">
                你是最早的一批用户——还没有人交回真实结果
              </span>
              。你在下方回传的每一条，都会成为这套算法的第一块基石，帮到和你条件相近的下一届考生。
            </>
          )}
          <span className="mt-0.5 block text-ink-500">
            用完之后，记得在下方「结果回传」交回你的真实选择与结局。
          </span>
        </div>
      </div>
    </div>
  );
}
