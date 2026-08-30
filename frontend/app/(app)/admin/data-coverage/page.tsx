"use client";

import { useEffect, useState } from "react";
import { Database, RefreshCw, TriangleAlert } from "lucide-react";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useAuthStore } from "@/stores/auth";
import { dataCoverageApi, type EntityCoverage } from "@/lib/api/data-coverage";

const MISSING_LABEL: Record<string, string> = {
  catalog: "招生目录",
  intel: "院校情报",
  scoreline: "分数线",
};

function RateRing({ label, rate, detail }: { label: string; rate: number; detail: string }) {
  const pct = Math.round(rate * 100);
  return (
    <div className="flex flex-col items-center gap-1 rounded-2xl border border-paper-300 bg-white p-5">
      <span className="text-xs text-ink-500">{label}</span>
      <span
        className={`font-display text-3xl font-semibold ${pct >= 80 ? "text-emerald-600" : pct >= 30 ? "text-amber-600" : "text-red-600"}`}
      >
        {pct}%
      </span>
      <span className="text-xs text-ink-400">{detail}</span>
    </div>
  );
}

export default function DataCoveragePage() {
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);
  const [data, setData] = useState<EntityCoverage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setData(await dataCoverageApi.coverage());
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hydrated && user) void load();
  }, [hydrated, user]);

  if (!hydrated || loading) return <LoadingState text="加载完整率数据..." />;
  if (error || !data)
    return (
      <EmptyState
        title="加载失败"
        description={error || "暂无数据"}
        action={
          <button
            onClick={() => void load()}
            className="rounded-lg border border-paper-300 px-4 py-1.5 text-sm text-ink-600 hover:bg-paper-100"
          >
            重试
          </button>
        }
      />
    );

  const { overall, top100 } = data;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display flex items-center gap-2 text-2xl font-semibold text-ink-800 tracking-tight">
            <Database className="h-6 w-6" /> 数据北极星：四件套完整率
          </h1>
          <p className="mt-1 text-sm text-ink-500">{data.definition}</p>
        </div>
        <button
          onClick={() => void load()}
          className="flex items-center gap-1 rounded-lg border border-paper-300 px-3 py-1.5 text-xs text-ink-600 hover:bg-paper-100"
        >
          <RefreshCw className="h-3.5 w-3.5" /> 刷新
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <RateRing
          label="Top100 热度院校"
          rate={top100.full_set_rate}
          detail={`${top100.full_set}/${top100.total} 所四件套齐全`}
        />
        <RateRing
          label="全部院校"
          rate={overall.full_set_rate}
          detail={`${overall.full_set}/${overall.schools_total} 所四件套齐全`}
        />
      </div>

      <div className="grid grid-cols-3 gap-4">
        {(
          [
            ["招生目录", overall.with_catalog],
            ["院校情报", overall.with_intel],
            ["有效分数线", overall.with_scoreline],
          ] as const
        ).map(([label, n]) => (
          <div key={label} className="rounded-2xl border border-paper-300 bg-white p-4 text-center">
            <p className="font-display text-xl font-semibold text-ink-800">{n}</p>
            <p className="mt-1 text-xs text-ink-500">{label}</p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-paper-300 bg-white">
        <div className="flex items-center justify-between border-b border-paper-200 px-5 py-3">
          <p className="flex items-center gap-1.5 text-sm font-semibold text-ink-700">
            <TriangleAlert className="h-4 w-4 text-amber-500" />
            Top100 待补院校（{top100.missing_total} 所）
          </p>
          <span className="text-xs text-ink-400">按软科排名排序</span>
        </div>
        {top100.missing_sample.length === 0 ? (
          <p className="px-5 py-6 text-center text-sm text-ink-400">Top100 已全部覆盖</p>
        ) : (
          <ul className="divide-y divide-paper-200">
            {top100.missing_sample.map((s) => (
              <li key={s.school} className="flex items-center justify-between px-5 py-2.5 text-sm">
                <span className="text-ink-700">
                  <span className="mr-2 text-xs text-ink-400">#{s.ranking}</span>
                  {s.school}
                </span>
                <span className="flex gap-1.5">
                  {s.missing.map((m) => (
                    <span
                      key={m}
                      className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-600"
                    >
                      缺{MISSING_LABEL[m] ?? m}
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        )}
        {top100.missing_total > top100.missing_sample.length && (
          <p className="border-t border-paper-200 px-5 py-2 text-center text-xs text-ink-400">
            仅显示前 {top100.missing_sample.length} 所，共 {top100.missing_total} 所待补
          </p>
        )}
      </div>
    </div>
  );
}
