"use client";

// frontend/app/(app)/self-discovery/page.tsx
// 「定位 · 认识自己」新首页（认识自己 V1）——从测评工具箱升级为人生设计工作台。
// 主线：人生设计访谈（/self-discovery/interview）；证据工具：职业测评/平衡轮/技能树；
// 产出：《个人人生设计蓝图》（/self-discovery/blueprint）。

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  Compass,
  Target,
  CircleDot,
  Network,
  ArrowRight,
  BookOpen,
  CheckCircle2,
} from "lucide-react";
import { assessmentApi, lifeDesignApi, lifeWheelApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";
import type { BlueprintSummary } from "@/types";

const CONV_KEY = "gradpath_self_discovery_conv";

interface EvidenceState {
  assessment: "loading" | "done" | "none";
  wheel: "loading" | "done" | "none";
}

export default function SelfDiscoveryPage() {
  const [loading, setLoading] = useState(true);
  const [hasOngoing, setHasOngoing] = useState(false);
  const [blueprint, setBlueprint] = useState<BlueprintSummary | null>(null);
  const [evidence, setEvidence] = useState<EvidenceState>({ assessment: "loading", wheel: "loading" });

  useEffect(() => {
    const conv = typeof window !== "undefined" ? window.localStorage.getItem(CONV_KEY) : null;
    setHasOngoing(!!conv);
    const results = { assessment: "none", wheel: "none" } as EvidenceState;
    Promise.allSettled([
      assessmentApi
        .getHistory()
        .then((h) => {
          if (h.length > 0) results.assessment = "done";
        })
        .catch(() => {}),
      lifeWheelApi
        .getLatest()
        .then((s) => {
          if (s) results.wheel = "done";
        })
        .catch(() => {}),
      lifeDesignApi
        .getLatestBlueprint()
        .then((b) => {
          if (b) setBlueprint({ id: b.id, title: b.title, status: b.status, version: b.version, created_at: b.created_at });
        })
        .catch(() => {}),
    ]).finally(() => {
      setEvidence(results);
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingState />;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* 主线 hero */}
      <div className="card overflow-hidden">
        <div className="bg-gradient-to-br from-brand-50 to-paper-50 p-6 sm:p-8">
          <div className="text-center">
            <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-sm mb-4">
              <Compass className="h-8 w-8 text-brand-600" strokeWidth={1.8} />
            </div>
            <h1 className="page-title">认识自己，然后设计它</h1>
            <p className="text-sm text-ink-400 mt-2 leading-relaxed max-w-lg mx-auto">
              这不是又一套测评。是一场来自斯坦福人生设计课的深度访谈：
              看清现状 → 分清真问题 → 三个五年版本 → 原型行动，
              终点是一份《个人人生设计蓝图》，并用真实报考数据检验你的每个版本。
            </p>
            <div className="mt-6">
              <Link
                href="/self-discovery/interview"
                className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-brand-700"
              >
                <Compass className="h-4 w-4" />
                {hasOngoing ? "继续我的人生设计访谈" : "开始人生设计访谈"}
                <ArrowRight className="h-4 w-4" />
              </Link>
              <p className="mt-2 text-[11px] text-ink-400">
                约 30-60 分钟 · 可分多次进行 · 你的测评和档案会自动作为背景
              </p>
            </div>
          </div>
        </div>

        {/* 四阶段旅程 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-5 pt-6">
          {[
            { n: "1", t: "你在这里", d: "看清现状仪表盘" },
            { n: "2", t: "指南针", d: "工作观与人生观" },
            { n: "3", t: "寻路", d: "心流与能量地图" },
            { n: "4", t: "奥德赛计划", d: "三个五年版本 + 数据体检" },
          ].map((s) => (
            <div key={s.n} className="rounded-lg border border-paper-200 bg-white p-3">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
                {s.n}
              </span>
              <p className="mt-2 text-sm font-medium text-ink-800">{s.t}</p>
              <p className="mt-0.5 text-[11px] text-ink-400 leading-snug">{s.d}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 产出：蓝图 */}
      {blueprint && (
        <Link
          href="/self-discovery/blueprint"
          className="block rounded-xl border border-brand-200 bg-gradient-to-br from-brand-50 to-white p-5 transition-all hover:shadow-md"
        >
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-100">
              <BookOpen className="h-6 w-6 text-brand-600" strokeWidth={1.8} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="font-display font-semibold text-ink-800">{blueprint.title}</h3>
                {blueprint.status === "completed" && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-medium text-brand-700">
                    <CheckCircle2 className="h-3 w-3" />
                    已完成
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-ink-400">
                你的个人人生设计蓝图 · 生成于 {formatDate(blueprint.created_at)}
              </p>
            </div>
            <ArrowRight className="h-4 w-4 text-ink-300 mt-1" />
          </div>
        </Link>
      )}

      {/* 证据工具 */}
      <div>
        <h2 className="font-display font-semibold text-ink-800 mb-1">证据工具</h2>
        <p className="text-xs text-ink-400 mb-3">
          测评与自评的结果会自动注入访谈，让人生设计师更懂你——做完的会亮起
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <EvidenceTool
            href="/assessment"
            icon={<Target className="h-6 w-6 text-blue-600" strokeWidth={1.8} />}
            name="职业测评"
            desc="霍兰德 3 分钟快测 / MBTI / 大五 / DISC"
            state={evidence.assessment}
          />
          <EvidenceTool
            href="/life-wheel"
            icon={<CircleDot className="h-6 w-6 text-emerald-600" strokeWidth={1.8} />}
            name="人生平衡轮"
            desc="8 维现状快照，访谈第一阶段的现成证据"
            state={evidence.wheel}
          />
          <EvidenceTool
            href="/skills"
            icon={<Network className="h-6 w-6 text-purple-600" strokeWidth={1.8} />}
            name="技能树"
            desc="想学 / 已掌握标记，寻路阶段的线索"
            state="none"
            hideState
          />
        </div>
      </div>
    </div>
  );
}

function EvidenceTool({
  href,
  icon,
  name,
  desc,
  state,
  hideState,
}: {
  href: string;
  icon: ReactNode;
  name: string;
  desc: string;
  state: "loading" | "done" | "none";
  hideState?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group rounded-xl border border-paper-300 bg-white p-5 transition-all hover:shadow-md",
        state === "done" && "border-brand-200 bg-brand-50/40",
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-paper-50">
          {icon}
        </div>
        {!hideState && state === "done" && (
          <span className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-medium text-brand-700">
            <CheckCircle2 className="h-3 w-3" />
            已入访谈
          </span>
        )}
      </div>
      <h3 className="mt-3 font-display font-semibold text-ink-800">{name}</h3>
      <p className="mt-1 text-xs text-ink-400 leading-relaxed">{desc}</p>
    </Link>
  );
}
