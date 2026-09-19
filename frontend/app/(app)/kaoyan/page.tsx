"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Newspaper, GraduationCap, Users } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/ui/empty";

const tabs = [
  { id: "news", label: "资讯中心", href: "/kaoyan/news", icon: Newspaper },
  { id: "community", label: "社区交流", href: "/kaoyan/community", icon: Users },
];

export default function KaoyanHomePage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <KaoyanHomePageContent />
    </Suspense>
  );
}

function KaoyanHomePageContent() {
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "";

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">考研工具箱</h1>
        <p className="text-ink-500">资讯中心与社区交流，两样真资产</p>
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
                  ? "text-brand-600 border-brand-600"
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
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 text-white">
              <GraduationCap className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-ink-900">考研一站式工具</h2>
              <p className="text-ink-500">打破信息差，让考研更简单</p>
            </div>
          </div>
        </div>

        {/* 功能入口卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <Link
                key={tab.id}
                href={`${tab.href}?from=kaoyan`}
                className="group bg-white rounded-xl p-5 border border-paper-200 hover:shadow-lg hover:border-brand-200 transition-all"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-brand-50 text-brand-600 group-hover:bg-brand-100 transition-colors">
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
    news: "考研资讯聚合，标注来源平台与质量等级，可跳转原文核对",
    community: "考研经验帖、问答、学长学姐交流",
  };
  return descriptions[tabId] || "";
}
