"use client";

// 考研信息站主页（009 T2 归口）：时间线 + 社区 + 外链目录 + 信任锚橱窗。
// 资讯中心 tab 隐藏——存量清空后空壳不上线（/kaoyan/news 页面保留诚实空态，
// 新供给随未来另案恢复）；禁"一站式工具"等已证伪话术（spec 文案纪律）。
import { CalendarRange, GraduationCap, ShieldCheck, Users } from "lucide-react";
import Link from "next/link";

import { ToolLinksBlock } from "@/components/tools/ToolLinksBlock";

const tabs = [
  { id: "timeline", label: "考试流程时间线", href: "/timeline", icon: CalendarRange },
  { id: "community", label: "社区交流", href: "/kaoyan/community", icon: Users },
];

function getTabDescription(tabId: string): string {
  const descriptions: Record<string, string> = {
    timeline: "考研全流程节点与官方时间锚点，替你盯信息差",
    community: "考研经验帖、问答、学长学姐交流",
    vault: "只上架带源数据：每条可溯源，查不到明说",
  };
  return descriptions[tabId] || "";
}

export default function KaoyanHomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">考研信息站</h1>
        <p className="text-ink-500">信息差候车室：时间线盯节点、社区问经验、橱窗查有源情报</p>
      </div>

      {/* Tab 切换（均为站内导航，离开本页） */}
      <div className="flex gap-2 mb-8 border-b border-paper-200 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <Link
              key={tab.id}
              href={`${tab.href}?from=kaoyan`}
              className="flex items-center gap-2 px-5 py-3 font-medium transition-all border-b-2 whitespace-nowrap text-ink-400 border-transparent hover:text-ink-600"
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </Link>
          );
        })}
      </div>

      {/* 归口内容：橱窗入口 + 外链目录 + 功能卡 */}
      <div className="space-y-6">
        <Link
          href="/kaoyan/vault"
          className="group flex items-center gap-4 rounded-xl p-6 border border-emerald-100 bg-gradient-to-r from-emerald-50 to-teal-50 hover:shadow-md transition-all"
        >
          <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 text-white">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-ink-900">信任锚橱窗</h2>
            <p className="text-sm text-ink-500">
              只上架带源数据：院校情报与研招网专业目录，每条可溯源；查不到明说，不编造
            </p>
          </div>
        </Link>

        <ToolLinksBlock />

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
                  <GraduationCap className="h-4 w-4 text-ink-300 ml-auto" />
                </div>
                <p className="text-sm text-ink-500">{getTabDescription(tab.id)}</p>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
