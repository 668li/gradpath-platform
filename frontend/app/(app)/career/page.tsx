"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { ClipboardCheck, Compass, ClipboardList, TrendingUp, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

const tabs = [
  { id: "assessment", label: "评估测试", icon: ClipboardCheck, color: "text-purple-500", href: "/assessment", desc: "霍兰德、MBTI、大五、DISC 四大职业测评，深度了解你的兴趣、人格与行为风格" },
  { id: "simulator", label: "路径模拟", icon: Compass, color: "text-green-500", href: "/career-simulator", desc: "模拟不同职业路径的发展轨迹，对比分析各方向的前景与风险" },
  { id: "decision-lab", label: "决策实验室", icon: ClipboardList, color: "text-blue-500", href: "/decision-lab", desc: "结构化决策框架，帮助你在多个职业选项中做出理性判断" },
  { id: "growth", label: "成长模式", icon: TrendingUp, color: "text-amber-500", href: "/growth-patterns", desc: "探索个人成长模式，制定可持续的自我提升策略" },
];

export default function CareerPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "assessment";
  const current = tabs.find((t) => t.id === activeTab) || tabs[0];

  const handleTabChange = (id: string) => {
    router.push(`/career?tab=${id}`);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">职业规划</h1>
        <p className="text-ink-500">从自我认知到决策落地，一站式职业探索工具集</p>
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
            <div className={cn(
              "flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-paper-50",
            )}>
              <current.icon className={cn("h-7 w-7", current.color)} strokeWidth={1.8} />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="font-display text-xl font-bold text-ink-800 mb-2">{current.label}</h2>
              <p className="text-sm text-ink-500 leading-relaxed mb-4">{current.desc}</p>
              <a
                href={current.href}
                className={cn(
                  "inline-flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-white transition-opacity hover:opacity-90",
                  current.id === "assessment" && "bg-purple-600",
                  current.id === "simulator" && "bg-green-600",
                  current.id === "decision-lab" && "bg-blue-600",
                  current.id === "growth" && "bg-amber-600",
                )}
              >
                开始
                <ChevronRight className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
