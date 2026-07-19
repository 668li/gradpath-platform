"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  GitBranch,
  Circle,
  Palette,
  Clock,
  RotateCcw,
  Lightbulb,
  BookOpen,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { growthPatternsApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { ListSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";

const tools = [
  { label: "个人看板", icon: LayoutDashboard, href: "/dashboard", color: "text-blue-500", desc: "总览成长数据、目标进度和关键指标" },
  { label: "技能树", icon: GitBranch, href: "/skills", color: "text-purple-500", desc: "可视化技能掌握程度，发现能力短板" },
  { label: "人生平衡轮", icon: Circle, href: "/life-wheel", color: "text-green-500", desc: "评估生活各维满意度，找到需平衡领域" },
  { label: "生活设计", icon: Palette, href: "/life-design", color: "text-pink-500", desc: "用设计思维重新规划生活" },
  { label: "时间线", icon: Clock, href: "/timeline", color: "text-amber-500", desc: "记录关键成长节点，回看发展轨迹" },
  { label: "回顾", icon: RotateCcw, href: "/retrospectives", color: "text-orange-500", desc: "定期复盘，持续迭代自我" },
  { label: "成长洞察", icon: Lightbulb, href: "/insights", color: "text-cyan-500", desc: "AI 驱动的成长分析" },
  { label: "学习方法", icon: BookOpen, href: "/learning-methods", color: "text-indigo-500", desc: "科学学习策略，提升效率" },
];

export default function GrowthPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  const load = useCallback(() => {
    setLoading(true);
    Promise.allSettled([growthPatternsApi.analyze(), growthPatternsApi.history()])
      .then(([a, h]) => {
        if (a.status === "fulfilled") setResult(a.value);
        if (h.status === "fulfilled") setHistory(h.value.items || []);
      })
      .catch(() => toast.push("加载成长档案失败", "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const reanalyze = () => {
    setAnalyzing(true);
    growthPatternsApi
      .analyze()
      .then((r) => {
        setResult(r);
        return growthPatternsApi.history();
      })
      .then((h) => setHistory(h.items || []))
      .catch(() => toast.push("分析失败", "error"))
      .finally(() => setAnalyzing(false));
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/15 text-brand-500">
            <TrendingUp className="h-6 w-6" strokeWidth={2} />
          </div>
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
              成长档案
            </h1>
            <p className="text-sm text-ink-500">
              聚合你的成长模式，跨期对比，发现隐藏规律。
            </p>
          </div>
        </div>
        <Button size="sm" onClick={reanalyze} loading={analyzing}>
          <Sparkles className="h-4 w-4" /> 重新分析
        </Button>
      </header>

      {loading ? (
        <ListSkeleton count={4} />
      ) : (
        <>
          {/* 成长得分 + 历史曲线 */}
          <section className="grid gap-4 md:grid-cols-3">
            <div className="card flex flex-col items-center justify-center p-6">
              <p className="text-sm text-ink-500">当前成长得分</p>
              <p className="font-display text-5xl font-bold text-brand-600">
                {result?.growth_score ?? 0}
              </p>
              <p className="mt-1 text-xs text-ink-400">
                发现 {result?.patterns?.length ?? 0} 个模式
              </p>
            </div>
            <div className="card col-span-2 p-5">
              <p className="mb-3 text-sm font-medium text-ink-600">成长得分历史</p>
              {history.length === 0 ? (
                <p className="text-sm text-ink-400">暂无历史，点击「重新分析」生成首个快照。</p>
              ) : (
                <div className="flex items-end gap-2 h-32">
                  {history.map((h) => (
                    <div key={h.id} className="flex flex-1 flex-col items-center gap-1">
                      <div
                        className="w-full rounded-t bg-brand-500/70"
                        style={{ height: `${Math.max(8, h.growth_score)}%` }}
                        title={`${h.period}: ${h.growth_score}`}
                      />
                      <span className="text-[10px] text-ink-400">{h.period}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* 发现的模式 */}
          <section className="card p-5">
            <h2 className="mb-3 flex items-center gap-2 font-semibold text-ink-800">
              <Lightbulb className="h-5 w-5 text-brand-500" /> 发现的成长模式
            </h2>
            {result?.patterns?.length > 0 ? (
              <div className="space-y-3">
                {result.patterns.map((p: any, i: number) => (
                  <div key={i} className="rounded-lg border border-paper-200 p-3">
                    <p className="font-medium text-ink-800">{p.title}</p>
                    <p className="mt-1 text-sm text-ink-500">{p.description}</p>
                    {p.suggestion && (
                      <p className="mt-1 text-sm text-brand-700">→ {p.suggestion}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="数据不足"
                description="多记录技能、决策与复盘后，管家会揭示你的成长模式。"
              />
            )}
          </section>

          {/* 成长工具 */}
          <section>
            <h2 className="mb-3 text-sm font-medium text-ink-600">成长工具</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {tools.map((t) => (
                <Link
                  key={t.href}
                  href={t.href}
                  className="card flex items-start gap-3 p-4 transition-shadow hover:shadow-md"
                >
                  <t.icon className={`h-6 w-6 ${t.color}`} strokeWidth={1.8} />
                  <div>
                    <p className="text-sm font-medium text-ink-800">{t.label}</p>
                    <p className="text-xs text-ink-400">{t.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
