"use client";

import { useSearchParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { Suspense } from "react";
import {
  Network,
  Target,
  UserCheck,
  BookOpen,
  Calendar,
  Trophy,
  Search,
  GraduationCap,
  School,
  Users,
  Lightbulb,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";

const tabs = [
  { id: "schools", label: "院校情报", href: "/kaoyan/schools", icon: School },
  { id: "compare", label: "院校对比", href: "/kaoyan/compare", icon: Network },
  { id: "predict", label: "录取预测", href: "/kaoyan/predict", icon: Target },
  { id: "mentors", label: "导师情报", href: "/kaoyan/mentors", icon: UserCheck },
  { id: "dark-knowledge", label: "暗知识", href: "/kaoyan/dark-knowledge", icon: Lightbulb },
  { id: "strategy", label: "备考策略", href: "/kaoyan/strategy", icon: BookOpen },
  { id: "community", label: "社区交流", href: "/kaoyan/community", icon: Users },
  { id: "plans", label: "学习计划", href: "/study-plans", icon: Calendar },
  { id: "outcome", label: "上岸报告", href: "/outcome-report", icon: Trophy },
];

export default function KaoyanHomePage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <KaoyanHomePageContent />
    </Suspense>
  );
}

function KaoyanHomePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "";

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">考研工具箱</h1>
        <p className="text-ink-500">选择功能，高效备考</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-8 border-b border-paper-200 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <Link
              key={tab.id}
              href={`${tab.href}?from=kaoyan`}
              className={cn(
                "flex items-center gap-2 px-5 py-3 font-medium transition-all border-b-2 whitespace-nowrap",
                isActive
                  ? "text-blue-600 border-blue-600"
                  : "text-ink-400 border-transparent hover:text-ink-600"
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </Link>
          );
        })}
      </div>

      {/* 欢迎内容 */}
      <div className="space-y-6">
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-8 border border-blue-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 text-white">
              <GraduationCap className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-ink-900">考研一站式工具</h2>
              <p className="text-ink-500">打破信息差，让考研更简单</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            {[
              { value: "100+", label: "院校数据", color: "text-blue-600" },
              { value: "44", label: "导师信息", color: "text-purple-600" },
              { value: "20+", label: "真实评价", color: "text-orange-600" },
              { value: "500+", label: "活跃用户", color: "text-green-600" },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className={cn("text-3xl font-bold", stat.color)}>
                  {stat.value}
                </div>
                <div className="text-sm text-ink-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* 功能入口卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <Link
                key={tab.id}
                href={`${tab.href}?from=kaoyan`}
                className="group bg-white rounded-xl p-5 border border-paper-200 hover:shadow-lg hover:border-blue-200 transition-all"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-100 transition-colors">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="font-semibold text-ink-800">{tab.label}</h3>
                </div>
                <p className="text-sm text-ink-500">
                  {getTabDescription(tab.id)}
                </p>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function getTabDescription(tabId: string): string {
  const descriptions: Record<string, string> = {
    schools: "10万+院校数据，分数线、招生计划、录取率一目了然",
    compare: "多维度对比院校，选出最适合你的学校",
    predict: "基于历年数据，智能预测录取概率",
    mentors: "289位导师信息，选对导师少走弯路",
    "dark-knowledge": "10万+条考研暗知识，那些没人告诉你的真相",
    strategy: "个性化推荐，高效备考策略",
    community: "考研经验帖、问答、学长学姐交流",
    plans: "制定学习计划，科学管理时间",
    outcome: "上岸学长学姐的经验分享",
  };
  return descriptions[tabId] || "";
}
