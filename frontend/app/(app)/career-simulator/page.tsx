"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Briefcase,
  Building2,
  ChevronDown,
  ChevronRight,
  GraduationCap,
  Info,
  Landmark,
  Play,
  Plus,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { careerSimulatorApi } from "@/lib/api";
import type {
  DistributionMetric,
  PathAnalysis,
  PathConfig,
  SimulateResponse,
} from "@/lib/api/career-simulator";
import { LoadingState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { Button, Input } from "@/components/ui/form-controls";
import { TestDriveSection } from "@/components/career-simulator/test-drive-card";

/**
 * 路径模拟器 v2 — 真数据胜率推演（2026-09-25 重构）。
 *
 * 范式转变：旧版"10 年薪资/满意度预测"在零纵向数据下只能输出编造的精确数
 * （诊断报告判死）；新版只呈现真实历史分布 + 你的位置 + 证据链：
 * - 每个数字带 P25/P50/P75 + 样本量 + 来源
 * - "你的位置"= 分数在真实分布中的百分位（描述统计，不是概率）
 * - 样本不足的维度如实降级，绝不硬算
 * - 三线结论叠加 path_decision_engine（继承劝退纪律/条件包/岗位级关联）
 */

type PathRow = {
  key: string;
  name: string;
  path_type: "grad" | "civil" | "career";
  target: string;
  estimated_score: number | null;
};

const PATH_LABELS: Record<string, string> = {
  grad: "考研",
  civil: "考公",
  career: "直接就业",
};
const PATH_ICONS: Record<string, React.ReactNode> = {
  grad: <GraduationCap className="h-4 w-4" />,
  civil: <Landmark className="h-4 w-4" />,
  career: <Briefcase className="h-4 w-4" />,
};
const GRAD_TIERS = [
  { id: "985", name: "985 层次" },
  { id: "211", name: "211 层次" },
];
const CIVIL_CLUSTERS = [
  { id: "general", name: "税务/统计/海事（综合口径）" },
  { id: "police", name: "公安/边检（含专业科目）" },
  { id: "central", name: "中央党群/部委" },
];

let rowSeq = 0;
const newRow = (partial?: Partial<PathRow>): PathRow => ({
  key: `row-${++rowSeq}`,
  name: partial?.name ?? "",
  path_type: partial?.path_type ?? "grad",
  target: partial?.target ?? "985",
  estimated_score: partial?.estimated_score ?? null,
});

export default function CareerSimulatorPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<PathRow[]>([
    newRow({ name: "考研 985", path_type: "grad", target: "985", estimated_score: 350 }),
    newRow({ name: "考公·税务系统", path_type: "civil", target: "general", estimated_score: 120 }),
  ]);
  const [major, setMajor] = useState("");
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState<Set<string>>(new Set());

  useEffect(() => {
    careerSimulatorApi.getPresets().catch(() => undefined);
  }, []);

  const toggleEvidence = (key: string) => {
    setEvidenceOpen((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const runSimulate = async (overrideRows?: PathRow[]) => {
    const active = overrideRows ?? rows;
    if (!active.length) return;
    setLoading(true);
    try {
      const payload: { paths: PathConfig[]; major?: string } = {
        paths: active.map((r) => ({
          name: r.name.trim() || PATH_LABELS[r.path_type],
          path_type: r.path_type,
          target: r.path_type === "career" ? null : r.target,
          estimated_score: r.estimated_score,
        })),
      };
      if (major.trim()) payload.major = major.trim();
      const resp = await careerSimulatorApi.simulate(payload);
      setResult(resp);
      requestAnimationFrame(() => {
        document.getElementById("sim-result")?.scrollIntoView({ behavior: "smooth" });
      });
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "推演失败，请稍后重试", "error");
    } finally {
      setLoading(false);
    }
  };

  const updateRow = (key: string, patch: Partial<PathRow>) => {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  };

  // 敏感度滑杆：改分后松手即时重算（分位重算是轻查询）
  const scoreSlider = (r: PathRow) => {
    const isGrad = r.path_type === "grad";
    const min = isGrad ? 250 : 90;
    const max = isGrad ? 450 : 160;
    return (
      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between text-xs text-ink-500">
          <span>
            {isGrad
              ? "初试预估总分（拖动后松手重算你的位置）"
              : "行测+申论模考总分（拖动后松手重算你的位置）"}
          </span>
          <span className="font-mono text-ink-700">{r.estimated_score ?? "未填"} 分</span>
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={1}
          value={r.estimated_score ?? min}
          onChange={(e) => updateRow(r.key, { estimated_score: Number(e.target.value) })}
          onMouseUp={() => runSimulate()}
          onTouchEnd={() => runSimulate()}
          className="w-full accent-brand-500"
          aria-label="预估分数滑杆"
        />
      </div>
    );
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-ink-900">
          <Activity className="h-6 w-6 text-brand-500" />
          路径模拟器 · 真数据推演
        </h1>
        <p className="mt-2 text-sm leading-6 text-ink-500">
          不预测未来，只呈现<b className="text-ink-700">真实历史分布</b>和你在其中的位置——
          报录比、进面线、官方薪资，每个数字可查样本量与来源；数据不足的地方会如实告诉你。
        </p>
      </header>

      {/* ── 配置区 ── */}
      <section className="rounded-xl border border-line-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink-700">选择要对比的路径（1-3 条）</h2>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setRows((p) => (p.length < 3 ? [...p, newRow()] : p))}
            disabled={rows.length >= 3}
          >
            <Plus className="mr-1 h-3.5 w-3.5" /> 加一条
          </Button>
        </div>

        <div className="space-y-3">
          {rows.map((r) => (
            <div key={r.key} className="rounded-lg border border-line-200 bg-ink-50/60 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  value={r.name}
                  onChange={(e) => updateRow(r.key, { name: e.target.value })}
                  placeholder="路径名（如：考研 985）"
                  className="w-36 !py-1.5 text-sm"
                />
                <div className="flex overflow-hidden rounded-lg border border-line-200">
                  {(["grad", "civil", "career"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() =>
                        updateRow(r.key, {
                          path_type: t,
                          target: t === "grad" ? "985" : t === "civil" ? "general" : "",
                        })
                      }
                      className={`flex items-center gap-1 px-3 py-1.5 text-xs transition-colors ${
                        r.path_type === t
                          ? "bg-brand-500 text-white"
                          : "bg-white text-ink-600 hover:bg-ink-100"
                      }`}
                    >
                      {PATH_ICONS[t]}
                      {PATH_LABELS[t]}
                    </button>
                  ))}
                </div>
                {r.path_type === "grad" && (
                  <select
                    value={r.target}
                    onChange={(e) => updateRow(r.key, { target: e.target.value })}
                    className="rounded-lg border border-line-200 bg-white px-2 py-1.5 text-xs"
                  >
                    {GRAD_TIERS.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                )}
                {r.path_type === "civil" && (
                  <select
                    value={r.target}
                    onChange={(e) => updateRow(r.key, { target: e.target.value })}
                    className="max-w-52 rounded-lg border border-line-200 bg-white px-2 py-1.5 text-xs"
                  >
                    {CIVIL_CLUSTERS.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                )}
                <button
                  onClick={() =>
                    setRows((p) => (p.length > 1 ? p.filter((x) => x.key !== r.key) : p))
                  }
                  className="ml-auto rounded-md p-1.5 text-ink-400 hover:bg-red-50 hover:text-red-500"
                  aria-label="删除此路径"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              {r.path_type !== "career" && scoreSlider(r)}
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div className="min-w-44 flex-1">
            <label className="mb-1 block text-xs text-ink-500">
              你的专业（选填，填了会叠加三线决策引擎的岗位级分析）
            </label>
            <Input
              value={major}
              onChange={(e) => setMajor(e.target.value)}
              placeholder="如：计算机"
              className="!py-1.5 text-sm"
            />
          </div>
          <Button onClick={() => runSimulate()} disabled={loading}>
            {loading ? (
              <RotateCcw className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-1 h-4 w-4" />
            )}
            {loading ? "正在对真实数据做统计…" : "开始推演"}
          </Button>
        </div>
      </section>

      {/* ── 结果区 ── */}
      <div id="sim-result" className="mt-6 scroll-mt-20">
        {loading && <LoadingState text="正在聚合真实数据分布…" />}
        {!loading && !result && (
          <div className="rounded-xl border border-dashed border-line-300 bg-white/60 p-10 text-center text-sm text-ink-400">
            <BarChart3 className="mx-auto mb-3 h-10 w-10 text-ink-300" />
            配置好路径后点「开始推演」——你会看到真实报录比/进面线分布和你的位置，
            而不是一堆编出来的"10 年后月薪预测"。
          </div>
        )}
        {!loading && result && (
          <div className="space-y-5">
            {result.paths.map((p, i) => (
              <PathCard
                key={`${p.name}-${i}`}
                path={p}
                evidenceOpen={evidenceOpen.has(`${p.name}-${i}`)}
                onToggleEvidence={() => toggleEvidence(`${p.name}-${i}`)}
              />
            ))}

            {result.engine_analysis?.recommendation && (
              <section className="rounded-xl border border-brand-200 bg-brand-50/50 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink-800">
                  <Building2 className="h-4 w-4 text-brand-500" />
                  三线决策引擎结论
                  <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-normal text-ink-400">
                    {result.engine_analysis.source}
                  </span>
                </h3>
                <p className="whitespace-pre-wrap text-sm leading-6 text-ink-600">
                  {result.engine_analysis.recommendation}
                </p>
              </section>
            )}

            <p className="flex items-start gap-1.5 px-1 text-xs leading-5 text-ink-400">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {result.method_note}
            </p>
          </div>
        )}
      </div>

      {/* 职业试驾（Forage 式，唯一保留的旧模块；锚点修复 2026-09-25） */}
      <div id="test-drive" className="mt-10 scroll-mt-20">
        <TestDriveSection />
      </div>
    </div>
  );
}

/* ── 单路径结果卡：位置卡 → 分布图 → 证据链 → 诚实缺口 ── */

function PathCard({
  path,
  evidenceOpen,
  onToggleEvidence,
}: {
  path: PathAnalysis;
  evidenceOpen: boolean;
  onToggleEvidence: () => void;
}) {
  const pos = path.your_position;
  return (
    <section className="rounded-xl border border-line-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {PATH_ICONS[path.path_type]}
        <h3 className="text-base font-semibold text-ink-900">{path.name}</h3>
        {pos?.percentile != null && (
          <span className="rounded-full bg-ink-100 px-2.5 py-0.5 text-xs font-medium text-ink-700">
            {pos.position_word} · P{pos.percentile}
          </span>
        )}
      </div>

      {pos ? (
        <div className="mb-4 rounded-lg border border-line-200 bg-ink-50/60 p-4">
          <p className="text-sm font-medium text-ink-800">{pos.metric}</p>
          <p className="mt-1 text-sm text-ink-500">
            参照中位数 P50 = <b className="font-mono">{pos.ref_p50}</b>
            {" — "}
            {pos.percentile != null && pos.percentile >= 50
              ? `该分布中 ${pos.percentile}% 的线不高于你的分`
              : `该分布中 ${100 - (pos.percentile ?? 0)}% 的线高于你的分`}
          </p>
          <p className="mt-2 text-xs text-ink-400">{path.disclaimer}</p>
        </div>
      ) : (
        path.estimated_score == null &&
        path.path_type !== "career" && (
          <p className="mb-4 text-xs text-ink-400">
            在上方滑杆填入预估分，可以看到你在分布中的位置。
          </p>
        )
      )}

      <div className="space-y-4">
        {path.metrics.map((m, i) => (
          <MetricBlock key={i} metric={m} score={path.estimated_score ?? null} />
        ))}
        {!path.metrics.length && (
          <p className="rounded-lg bg-ink-50 p-4 text-sm text-ink-500">
            这个方向暂时没有足够的真实数据做分布参照（见下方说明），我们不会编数字。
          </p>
        )}
      </div>

      {path.carding_rate && path.carding_rate.total >= 5 && (
        <p className="mt-3 flex items-start gap-1.5 text-xs text-ink-500">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
          {path.carding_rate.note}
        </p>
      )}

      {(path.sample_note || path.metrics.length > 0) && (
        <button
          onClick={onToggleEvidence}
          className="mt-4 flex w-full items-center gap-1 rounded-lg bg-ink-50 px-3 py-2 text-left text-xs text-ink-500 hover:bg-ink-100"
        >
          {evidenceOpen ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
          数据来源与样本量（每个数字都可查）
        </button>
      )}
      {evidenceOpen && (
        <div className="mt-2 space-y-2 rounded-lg border border-line-200 p-3 text-xs text-ink-500">
          {path.sample_note && <p>· {path.sample_note}</p>}
          {path.data_note && <p>· {path.data_note}</p>}
          {path.metrics.map((m, i) => (
            <p key={i}>
              · {m.label}：N={m.sample_size ?? "官方口径"}，来源 {m.source}
              {m.source_url && (
                <>
                  {" "}
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-500 underline"
                  >
                    官方链接
                  </a>
                </>
              )}
            </p>
          ))}
        </div>
      )}

      {path.honest_gaps.length > 0 && (
        <div className="mt-4 rounded-lg border border-dashed border-line-300 p-3">
          <p className="mb-1 text-xs font-medium text-ink-500">这些我们给不了（如实说明）：</p>
          <ul className="list-inside list-disc space-y-0.5 text-xs text-ink-400">
            {path.honest_gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

/* 分布块：五分位 + 直方图 + 你的位置标记 */
function MetricBlock({ metric, score }: { metric: DistributionMetric; score: number | null }) {
  const dist = metric.distribution ?? [];
  const hasDist = Array.isArray(metric.distribution) && dist.length >= 5;
  const distKey = dist.join(",");

  const histogram = useMemo(() => {
    if (!hasDist) return null;
    const min = Math.min(...dist);
    const max = Math.max(...dist);
    const bins = 20;
    const width = (max - min) / bins || 1;
    const counts = new Array(bins).fill(0);
    for (const v of dist) {
      const idx = Math.min(bins - 1, Math.floor((v - min) / width));
      counts[idx] += 1;
    }
    const maxCount = Math.max(...counts, 1);
    const scoreBin =
      score != null && score >= min && score <= max
        ? Math.min(bins - 1, Math.floor((score - min) / width))
        : null;
    return { bins: counts.map((c) => Math.round((c / maxCount) * 100)), min, max, scoreBin };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasDist, distKey, score]);

  return (
    <div className="rounded-lg border border-line-100 p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-ink-700">{metric.label}</p>
        <p className="font-mono text-sm text-ink-800">
          {metric.value != null ? (
            <>
              {metric.value.toLocaleString()} <span className="text-xs text-ink-400">{metric.unit}</span>
            </>
          ) : (
            <>
              P25 <b>{metric.p25}</b> · P50 <b>{metric.p50}</b> · P75 <b>{metric.p75}</b>{" "}
              <span className="text-xs text-ink-400">{metric.unit}</span>
            </>
          )}
        </p>
      </div>
      {metric.direction === "lower_better" && (
        <p className="mt-1 text-xs text-ink-400">报录比越低竞争越小；P50 是该层次的中位水平</p>
      )}
      {histogram && (
        <div className="mt-3">
          <div className="flex h-20 items-end gap-0.5">
            {histogram.bins.map((h, i) => (
              <div key={i} className="relative flex-1">
                <div
                  className={`w-full rounded-t-sm ${i === histogram.scoreBin ? "bg-brand-500" : "bg-brand-200"}`}
                  style={{ height: `${Math.max(h, 3)}%` }}
                />
                {i === histogram.scoreBin && (
                  <span className="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-bold text-brand-600">
                    你
                  </span>
                )}
              </div>
            ))}
          </div>
          <div className="mt-1 flex justify-between font-mono text-[10px] text-ink-400">
            <span>{Math.round(histogram.min)}</span>
            <span>{Math.round((histogram.min + histogram.max) / 2)}</span>
            <span>{Math.round(histogram.max)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
