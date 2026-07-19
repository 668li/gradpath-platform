"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  LayoutDashboard,
  GitBranch,
  Circle,
  Palette,
  Clock,
  RotateCcw,
  Lightbulb,
  BookOpen,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const tabs = [
  { id: "dashboard", label: "个人看板", icon: LayoutDashboard, color: "text-blue-500", href: "/dashboard", desc: "总览你的成长数据、目标进度和关键指标" },
  { id: "skills", label: "技能树", icon: GitBranch, color: "text-purple-500", href: "/skills", desc: "可视化技能掌握程度，发现能力短板与发展方向" },
  { id: "life-wheel", label: "人生平衡轮", icon: Circle, color: "text-green-500", href: "/life-wheel", desc: "评估生活各维度的满意度，找到需要平衡的领域" },
  { id: "life-design", label: "生活设计", icon: Palette, color: "text-pink-500", href: "/life-design", desc: "用设计思维重新规划你的生活，探索更多可能性" },
  { id: "timeline", label: "时间线", icon: Clock, color: "text-amber-500", href: "/timeline", desc: "记录关键成长节点，回看你的发展轨迹" },
  { id: "retrospectives", label: "回顾", icon: RotateCcw, color: "text-orange-500", href: "/retrospectives", desc: "定期复盘，总结经验教训，持续迭代自我" },
  { id: "insights", label: "成长洞察", icon: Lightbulb, color: "text-cyan-500", href: "/insights", desc: "AI 驱动的成长分析，发现隐藏的模式和趋势" },
  { id: "learning-methods", label: "学习方法", icon: BookOpen, color: "text-indigo-500", href: "/learning-methods", desc: "科学的学习策略与方法论，提升学习效率" },
];

export default function GrowthPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "dashboard";
  const current = tabs.find((t) => t.id === activeTab) || tabs[0];

  const handleTabChange = (id: string) => {
    router.push(`/growth?tab=${id}`);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">成长追踪</h1>
        <p className="text-ink-500">记录、分析、优化你的个人成长路径</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-8 border-b border-paper-200 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={cn(
                "flex items-center gap-2 px-6 py-3 font-medium transition-all border-b-2 whitespace-nowrap",
                activeTab === tab.id
                  ? `${tab.color} border-current`
                  : "text-ink-400 border-transparent hover:text-ink-600"
              )}
            >
              <Icon className="h-5 w-5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* 内容区域 - 卡片链接 */}
      <div className="mt-8 max-w-2xl">
        <div className="bg-white rounded-xl border border-paper-200 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-paper-50">
              <current.icon className={cn("h-7 w-7", current.color)} strokeWidth={1.8} />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="font-display text-xl font-bold text-ink-800 mb-2">{current.label}</h2>
              <p className="text-sm text-ink-500 leading-relaxed mb-4">{current.desc}</p>
              <a
                href={current.href}
                className={cn(
                  "inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-white transition-opacity hover:opacity-90",
                  current.id === "dashboard" && "bg-blue-600",
                  current.id === "skills" && "bg-purple-600",
                  current.id === "life-wheel" && "bg-green-600",
                  current.id === "life-design" && "bg-pink-600",
                  current.id === "timeline" && "bg-amber-600",
                  current.id === "retrospectives" && "bg-orange-600",
                  current.id === "insights" && "bg-cyan-600",
                  current.id === "learning-methods" && "bg-indigo-600",
                )}
              >
                前往
                <ChevronRight className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
