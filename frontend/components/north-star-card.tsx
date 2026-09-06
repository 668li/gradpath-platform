"use client";

/**
 * 北极星度量卡片（管理员可见）：条件完成率 + 回传率 + 近 8 周趋势。
 * 数据源 GET /api/north-star/summary（admin 门控）。
 * 非管理员请求返回 403 → 本组件静默不渲染（前端无需感知角色）。
 */

import { useApi } from "@/lib/api/swr-config";

interface NorthStarSummary {
  condition_completion: { met: number; total: number; ratio: number | null };
  outcome_response: {
    total: number;
    responded: number;
    ratio: number | null;
    avg_satisfaction: number | null;
  };
  weekly: {
    week: string;
    decisions: number;
    responded: number;
    condition_records: number;
    condition_met: number;
  }[];
}

const pct = (r: number | null | undefined) =>
  r === null || r === undefined ? "—" : `${(r * 100).toFixed(1)}%`;

export function NorthStarCard() {
  // useApi 走项目统一 fetcher（带鉴权头与错误规范化）；非管理员 403 → error 置位 → 不渲染
  const { data, error } = useApi<NorthStarSummary>("/api/north-star/summary");

  if (error || !data) return null; // 非管理员 / 加载前不渲染

  const cc = data.condition_completion;
  const oc = data.outcome_response;
  const maxDecisions = Math.max(1, ...data.weekly.map((w) => w.decisions));

  return (
    <section
      aria-label="北极星度量"
      className="mb-6 rounded-xl border border-brand-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-ink-900">🔭 北极星度量</h2>
        <span className="text-xs text-ink-400">近 8 周趋势 · 管理员视图</span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <div className="text-2xl font-bold text-brand-600">{pct(cc.ratio)}</div>
          <div className="text-xs text-ink-500">
            条件完成率 ({cc.met}/{cc.total})
          </div>
        </div>
        <div>
          <div className="text-2xl font-bold text-brand-600">{pct(oc.ratio)}</div>
          <div className="text-xs text-ink-500">
            回传率 ({oc.responded}/{oc.total})
          </div>
        </div>
        <div>
          <div className="text-2xl font-bold text-ink-900">
            {oc.avg_satisfaction ?? "—"}
          </div>
          <div className="text-xs text-ink-500">回传满意度均分</div>
        </div>
        <div>
          <div className="flex h-10 items-end gap-1">
            {data.weekly.map((w) => (
              <div
                key={w.week}
                title={`${w.week}: ${w.decisions} 次决策 / ${w.responded} 回传`}
                className="w-full rounded-t bg-brand-300"
                style={{ height: `${Math.max(8, (w.decisions / maxDecisions) * 40)}px` }}
              />
            ))}
          </div>
          <div className="mt-1 text-xs text-ink-500">每周决策量</div>
        </div>
      </div>
    </section>
  );
}
