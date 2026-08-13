"use client";

// frontend/components/career-simulator/path-comparison-table.tsx
// 多路径 What-If 对比组件 — PathComparisonTable + WhatIfSection

import { useState } from "react";
import Link from "next/link";
import {
  GitCompareArrows, Play, Plus, Trash2, ArrowRight,
  GraduationCap, Briefcase, Landmark, Rocket, Plane, Trophy,
  CheckCircle2, AlertCircle, Clock, TrendingUp, ShieldAlert, Heart,
} from "lucide-react";
import { pathComparisonApi } from "@/lib/api";
import type {
  PathInput, PathMetrics, ComparisonResponse, PathType, RiskLevel,
} from "@/types/path-comparison";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

// 6 种预设路径元信息（与后端 PATH_PRESETS 对齐）
const PATH_PRESETS: { value: PathType; label: string; icon: React.ReactNode; gradient: string }[] = [
  { value: "kaoyan", label: "考研深造", icon: <GraduationCap className="w-4 h-4" />, gradient: "from-blue-500 to-indigo-600" },
  { value: "employment", label: "直接就业", icon: <Briefcase className="w-4 h-4" />, gradient: "from-emerald-500 to-teal-600" },
  { value: "civil_service", label: "考公", icon: <Landmark className="w-4 h-4" />, gradient: "from-amber-500 to-orange-600" },
  { value: "big_tech", label: "跳槽大厂", icon: <Trophy className="w-4 h-4" />, gradient: "from-purple-500 to-fuchsia-600" },
  { value: "startup", label: "创业", icon: <Rocket className="w-4 h-4" />, gradient: "from-rose-500 to-pink-600" },
  { value: "phd_abroad", label: "出国读博", icon: <Plane className="w-4 h-4" />, gradient: "from-cyan-500 to-sky-600" },
];

const PATH_LABEL: Record<string, string> = Object.fromEntries(
  PATH_PRESETS.map((p) => [p.value, p.label]),
);

const PATH_ICON: Record<string, React.ReactNode> = Object.fromEntries(
  PATH_PRESETS.map((p) => [p.value, p.icon]),
);

const PATH_GRADIENT: Record<string, string> = Object.fromEntries(
  PATH_PRESETS.map((p) => [p.value, p.gradient]),
);

// 风险等级 Badge 配色
const RISK_BADGE: Record<RiskLevel, { label: string; className: string }> = {
  low: { label: "低风险", className: "bg-green-100 text-green-700 border-green-200" },
  medium: { label: "中风险", className: "bg-amber-100 text-amber-700 border-amber-200" },
  high: { label: "高风险", className: "bg-red-100 text-red-700 border-red-200" },
};

// 解析收入区间上限用于渐变色计算
function incomeUpper(s: string): number {
  try {
    const tail = s.split("-").pop() || "";
    return parseInt(tail.replace(/\D/g, ""), 10) || 0;
  } catch {
    return 0;
  }
}

// 根据值返回背景渐变（低→高，浅→深）
function incomeGradient(value: number, max: number): string {
  if (max <= 0) return "bg-ink-50";
  const ratio = Math.min(1, value / max);
  if (ratio >= 0.75) return "bg-emerald-100";
  if (ratio >= 0.5) return "bg-blue-100";
  if (ratio >= 0.25) return "bg-amber-100";
  return "bg-rose-100";
}

// 环形进度（SVG）— 匹配度
function RingProgress({ value, size = 44 }: { value: number; size?: number }) {
  const stroke = 4;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.max(0, Math.min(100, value)) / 100) * c;
  const color = value >= 70 ? "#10b981" : value >= 50 ? "#3b82f6" : "#ef4444";
  return (
    <svg width={size} height={size} className="inline-block">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
        strokeWidth={stroke} strokeDasharray={c} strokeDashoffset={offset}
        strokeLinecap="round" transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        className="text-[10px] font-bold" fill={color}>
        {value}
      </text>
    </svg>
  );
}

interface PathComparisonTableProps {
  metrics: PathMetrics[];
}

/**
 * PathComparisonTable — 对比表格
 * 行：每条路径；列：维度（收入1/3/5年、风险、成长性、时间成本、匹配度）
 * - 收入用渐变色背景（低→高）
 * - 风险用 Badge（绿/黄/红）
 * - 成长性用进度条
 * - 匹配度用百分比 + 环形图
 */
export function PathComparisonTable({ metrics }: PathComparisonTableProps) {
  if (!metrics.length) return null;

  // 计算 5 年收入上限，用于背景渐变归一化
  const maxIncome5y = Math.max(...metrics.map((m) => incomeUpper(m.income_5y)), 1);
  const maxGrowth = 10;

  return (
    <div className="overflow-x-auto rounded-xl border border-ink-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-ink-50 text-ink-600">
          <tr>
            <th className="px-4 py-3 text-left font-medium sticky left-0 bg-ink-50 z-10">路径</th>
            <th className="px-4 py-3 text-center font-medium">1 年收入</th>
            <th className="px-4 py-3 text-center font-medium">3 年收入</th>
            <th className="px-4 py-3 text-center font-medium">5 年收入</th>
            <th className="px-4 py-3 text-center font-medium">风险</th>
            <th className="px-4 py-3 text-center font-medium">成长性</th>
            <th className="px-4 py-3 text-center font-medium">时间成本</th>
            <th className="px-4 py-3 text-center font-medium">匹配度</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m, idx) => {
            const gradient = PATH_GRADIENT[m.path_type] || "from-ink-400 to-ink-500";
            const risk = RISK_BADGE[m.risk_level] || RISK_BADGE.medium;
            return (
              <tr key={`${m.path_type}-${m.target_role}-${idx}`} className="border-t hover:bg-ink-50/50">
                {/* 路径 */}
                <td className="px-4 py-3 sticky left-0 bg-white z-10">
                  <div className="flex items-center gap-2">
                    <span className={cn("inline-flex items-center justify-center h-8 w-8 rounded-lg bg-gradient-to-br text-white", gradient)}>
                      {PATH_ICON[m.path_type] || <Briefcase className="w-4 h-4" />}
                    </span>
                    <div className="min-w-0">
                      <div className="font-medium text-ink-900 truncate max-w-[160px]">{m.target_role}</div>
                      <div className="text-xs text-ink-500">{PATH_LABEL[m.path_type] || m.path_type}</div>
                    </div>
                  </div>
                </td>
                {/* 收入 1y */}
                <td className={cn("px-4 py-3 text-center font-medium", incomeGradient(incomeUpper(m.income_1y), maxIncome5y))}>
                  {m.income_1y}
                </td>
                <td className={cn("px-4 py-3 text-center font-medium", incomeGradient(incomeUpper(m.income_3y), maxIncome5y))}>
                  {m.income_3y}
                </td>
                <td className={cn("px-4 py-3 text-center font-medium", incomeGradient(incomeUpper(m.income_5y), maxIncome5y))}>
                  {m.income_5y}
                </td>
                {/* 风险 */}
                <td className="px-4 py-3 text-center">
                  <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border", risk.className)}>
                    <ShieldAlert className="w-3 h-3" />
                    {risk.label}
                  </span>
                  <div className="mt-1 text-[11px] text-ink-500 max-w-[180px] mx-auto leading-snug">
                    {m.risk_description}
                  </div>
                </td>
                {/* 成长性 */}
                <td className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-16 h-2 bg-ink-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                        style={{ width: `${(m.growth_score / maxGrowth) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-ink-700">{m.growth_score}/10</span>
                  </div>
                </td>
                {/* 时间成本 */}
                <td className="px-4 py-3 text-center">
                  <div className="inline-flex items-center gap-1 text-ink-700">
                    <Clock className="w-3.5 h-3.5 text-ink-400" />
                    <span className="font-medium">{m.time_cost_months}</span>
                    <span className="text-xs text-ink-500">个月</span>
                  </div>
                </td>
                {/* 匹配度 */}
                <td className="px-4 py-3 text-center">
                  <div className="flex flex-col items-center gap-1">
                    <RingProgress value={m.match_score} />
                    <div className="text-[11px] text-ink-500 max-w-[140px] leading-snug">
                      {m.match_description}
                    </div>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ----------------------------------------------------------------------
// WhatIfSection — What-If 分析区域
// ----------------------------------------------------------------------

const DEFAULT_PATHS: PathInput[] = [
  { path_type: "kaoyan", target_role: "算法工程师" },
  { path_type: "employment", target_role: "后端开发" },
];

export function WhatIfSection() {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [paths, setPaths] = useState<PathInput[]>(DEFAULT_PATHS);
  const [result, setResult] = useState<ComparisonResponse | null>(null);

  const addPath = () => {
    if (paths.length >= 3) return;
    setPaths([...paths, { path_type: "big_tech", target_role: "" }]);
  };

  const removePath = (idx: number) => {
    if (paths.length <= 2) return;
    setPaths(paths.filter((_, i) => i !== idx));
  };

  const updatePath = (idx: number, field: keyof PathInput, value: string) => {
    setPaths(paths.map((p, i) => (i === idx ? { ...p, [field]: value } : p)));
  };

  const handleCompare = async () => {
    if (paths.length < 2) {
      toast.error("至少选择 2 条路径进行对比");
      return;
    }
    const invalid = paths.find((p) => !p.target_role.trim());
    if (invalid) {
      toast.error("每条路径都需填写目标角色");
      return;
    }
    setLoading(true);
    try {
      const data = await pathComparisonApi.compare(paths);
      setResult(data);
      toast.success("对比完成，查看下方综合建议");
    } catch {
      toast.error("对比失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  // 维度最优路径高亮（按 5 年收入上限、最低风险、最高成长性、最低时间成本、最高匹配度）
  const best = result ? pickBest(result.metrics) : null;

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mt-6">
      {/* 标题 */}
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-ink-900 flex items-center gap-2">
          <GitCompareArrows className="w-5 h-5 text-purple-600" />
          What-If 路径对比 — 量化权衡 2-3 条职业路径
        </h2>
        <p className="mt-1 text-sm text-ink-500">
          选 2-3 条路径，从收入 / 风险 / 成长性 / 时间成本 / 匹配度 5 个维度做量化对比，并给出条件式建议。
        </p>
      </div>

      {/* 路径选择器 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
        {paths.map((p, idx) => {
          const gradient = PATH_GRADIENT[p.path_type] || "from-ink-400 to-ink-500";
          return (
            <div key={idx} className="relative border border-ink-200 rounded-lg p-3 bg-ink-50/60">
              {paths.length > 2 && (
                <button
                  onClick={() => removePath(idx)}
                  className="absolute top-2 right-2 text-ink-400 hover:text-red-500"
                  aria-label="移除路径"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <div className="flex items-center gap-2 mb-2">
                <span className={cn("inline-flex items-center justify-center h-7 w-7 rounded-md bg-gradient-to-br text-white", gradient)}>
                  {PATH_ICON[p.path_type] || <Briefcase className="w-3.5 h-3.5" />}
                </span>
                <span className="text-xs font-medium text-ink-500">路径 {idx + 1}</span>
              </div>
              <label className="block">
                <span className="block text-xs text-ink-500 mb-1">路径类型</span>
                <select
                  value={p.path_type}
                  onChange={(e) => updatePath(idx, "path_type", e.target.value)}
                  className="w-full border rounded px-2 py-1.5 text-sm bg-white"
                >
                  {PATH_PRESETS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </label>
              <label className="block mt-2">
                <span className="block text-xs text-ink-500 mb-1">目标角色</span>
                <input
                  type="text"
                  value={p.target_role}
                  onChange={(e) => updatePath(idx, "target_role", e.target.value)}
                  placeholder="如 后端开发 / 选调生 / SaaS 创业"
                  className="w-full border rounded px-2 py-1.5 text-sm bg-white"
                />
              </label>
            </div>
          );
        })}
        {paths.length < 3 && (
          <button
            onClick={addPath}
            className="border-2 border-dashed rounded-lg p-3 flex flex-col items-center justify-center text-ink-400 hover:text-purple-500 hover:border-purple-300 min-h-[160px]"
          >
            <Plus className="w-6 h-6 mb-1" />
            <span className="text-sm">添加第 {paths.length + 1} 条路径</span>
          </button>
        )}
      </div>

      {/* 开始对比 */}
      <div className="flex justify-center mb-4">
        <button
          onClick={handleCompare}
          disabled={loading || paths.length < 2}
          className="inline-flex items-center gap-1.5 bg-gradient-to-r from-purple-600 to-fuchsia-600 hover:from-purple-700 hover:to-fuchsia-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {loading ? "对比中…" : "开始对比"}
        </button>
      </div>

      {/* 加载 / 结果 / 空状态 */}
      {loading && <LoadingState text="正在生成 5 维量化对比…" />}

      {!loading && result && (
        <div className="space-y-5">
          <PathComparisonTable metrics={result.metrics} />

          {/* 维度最优标签条 */}
          {best && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
              <BestBadge label="收入上限" target={best.income.target_role} icon={<TrendingUp className="w-3 h-3" />} color="bg-emerald-50 text-emerald-700 border-emerald-200" />
              <BestBadge label="最低风险" target={best.risk.target_role} icon={<ShieldAlert className="w-3 h-3" />} color="bg-green-50 text-green-700 border-green-200" />
              <BestBadge label="最高成长" target={best.growth.target_role} icon={<TrendingUp className="w-3 h-3" />} color="bg-purple-50 text-purple-700 border-purple-200" />
              <BestBadge label="时间最短" target={best.time.target_role} icon={<Clock className="w-3 h-3" />} color="bg-blue-50 text-blue-700 border-blue-200" />
              <BestBadge label="最匹配" target={best.match.target_role} icon={<Heart className="w-3 h-3" />} color="bg-rose-50 text-rose-700 border-rose-200" />
            </div>
          )}

          {/* 综合建议卡片（高亮显示） */}
          <div className="rounded-xl bg-gradient-to-br from-purple-50 via-fuchsia-50 to-indigo-50 border border-purple-200 p-5">
            <div className="flex items-start gap-3">
              <div className="inline-flex items-center justify-center h-9 w-9 rounded-lg bg-gradient-to-br from-purple-600 to-fuchsia-600 text-white flex-shrink-0">
                <Trophy className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-ink-900 mb-2">综合建议</h3>
                <div className="text-sm text-ink-700 whitespace-pre-line leading-relaxed">
                  {result.recommendation}
                </div>
              </div>
            </div>
          </div>

          {/* 优劣势展开 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {result.metrics.map((m, idx) => (
              <div key={`${m.path_type}-${idx}`} className="border border-ink-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={cn("inline-flex items-center justify-center h-6 w-6 rounded bg-gradient-to-br text-white", PATH_GRADIENT[m.path_type] || "from-ink-400 to-ink-500")}>
                    {PATH_ICON[m.path_type] || <Briefcase className="w-3 h-3" />}
                  </span>
                  <span className="font-medium text-ink-900 text-sm">{m.target_role}</span>
                  <span className="text-xs text-ink-500">({PATH_LABEL[m.path_type] || m.path_type})</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="flex items-center gap-1 text-green-600 mb-1">
                      <CheckCircle2 className="w-3 h-3" /> 优势
                    </div>
                    <ul className="space-y-1 text-ink-600 list-disc pl-4">
                      {m.pros.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div className="flex items-center gap-1 text-red-600 mb-1">
                      <AlertCircle className="w-3 h-3" /> 劣势
                    </div>
                    <ul className="space-y-1 text-ink-600 list-disc pl-4">
                      {m.cons.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 底部引导：选一条路径做深度分析 */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link
              href="/decision-lab?from=comparison"
              className="inline-flex items-center gap-1.5 text-purple-600 hover:text-purple-700 text-sm font-medium px-4 py-2 rounded-lg bg-purple-50 hover:bg-purple-100 transition-colors"
            >
              选一条路径做深度分析 <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}

      {!loading && !result && (
        <EmptyState
          title="选 2-3 条路径开始 What-If 对比"
          description="量化对比收入、风险、成长性、时间成本与个人匹配度，得到条件式综合建议。"
        />
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// 维度最优路径选择
// ----------------------------------------------------------------------
function pickBest(metrics: PathMetrics[]) {
  const order: Record<RiskLevel, number> = { low: 0, medium: 1, high: 2 };
  return {
    income: metrics.reduce((a, b) => incomeUpper(b.income_5y) > incomeUpper(a.income_5y) ? b : a),
    risk: metrics.reduce((a, b) => order[b.risk_level] < order[a.risk_level] ? b : a),
    growth: metrics.reduce((a, b) => b.growth_score > a.growth_score ? b : a),
    time: metrics.reduce((a, b) => b.time_cost_months < a.time_cost_months ? b : a),
    match: metrics.reduce((a, b) => b.match_score > a.match_score ? b : a),
  };
}

function BestBadge({ label, target, icon, color }: {
  label: string;
  target: string;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className={cn("rounded-lg border px-2 py-1.5 flex flex-col gap-0.5", color)}>
      <div className="flex items-center gap-1 font-medium">
        {icon}
        <span>{label}</span>
      </div>
      <div className="truncate text-[11px] opacity-80">{target}</div>
    </div>
  );
}
