"use client";

import { useState } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  GitBranch,
  Circle,
  Clock,
  RotateCcw,
  Trophy,
  TrendingUp,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "概览", icon: LayoutDashboard },
  { id: "skills", label: "技能树", icon: GitBranch },
  { id: "wheel", label: "平衡轮", icon: Circle },
  { id: "timeline", label: "时间线", icon: Clock },
  { id: "review", label: "回顾", icon: RotateCcw },
  { id: "achievements", label: "成就", icon: Trophy },
];

const TAB_CONTENT: Record<string, { title: string; desc: string; href: string; color: string }> = {
  overview: {
    title: "个人看板",
    desc: "总览成长数据、目标进度和关键指标，快速了解你的发展全貌",
    href: "/dashboard",
    color: "text-blue-500",
  },
  skills: {
    title: "技能树",
    desc: "可视化技能掌握程度，发现能力短板，规划学习路径",
    href: "/skills",
    color: "text-purple-500",
  },
  wheel: {
    title: "人生平衡轮",
    desc: "评估生活各维度满意度，找到需要平衡的领域",
    href: "/life-wheel",
    color: "text-green-500",
  },
  timeline: {
    title: "成长时间线",
    desc: "记录关键成长节点，回看发展轨迹，发现成长规律",
    href: "/timeline",
    color: "text-amber-500",
  },
  review: {
    title: "成长回顾",
    desc: "定期复盘，持续迭代自我，从经验中提炼智慧",
    href: "/retrospectives",
    color: "text-orange-500",
  },
  achievements: {
    title: "成就墙",
    desc: "汇集你的里程碑与荣誉，见证每一步成长",
    href: "/achievements",
    color: "text-rose-500",
  },
};

export default function GrowthArchivePage() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/15 text-brand-500">
          <TrendingUp className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-800">
            成长档案
          </h1>
          <p className="text-sm text-ink-500">
            聚合你的成长数据，跨期对比，发现隐藏规律。
          </p>
        </div>
      </header>

      <div className="flex gap-2 border-b border-paper-300 pb-2 overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition-colors whitespace-nowrap",
                activeTab === tab.id
                  ? "bg-white text-brand-600 border-b-2 border-brand-500"
                  : "text-ink-400 hover:text-ink-600 hover:bg-paper-200",
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {(() => {
          const content = TAB_CONTENT[activeTab];
          const Icon = TABS.find((t) => t.id === activeTab)?.icon ?? LayoutDashboard;
          return (
            <Link
              key={activeTab}
              href={content.href}
              className="col-span-full bg-white rounded-xl border border-paper-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center gap-4">
                <div className={cn("p-3 rounded-xl bg-paper-100", content.color)}>
                  <Icon className="h-6 w-6" strokeWidth={1.8} />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-semibold text-ink-800">{content.title}</h2>
                  <p className="mt-1 text-sm text-ink-500">{content.desc}</p>
                </div>
                <ArrowRight className="h-5 w-5 text-ink-300 shrink-0" />
              </div>
            </Link>
          );
        })()}
      </div>
    </div>
  );
}