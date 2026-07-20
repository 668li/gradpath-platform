"use client";

import { useState } from "react";
import Link from "next/link";
import { GraduationCap, Landmark, Briefcase, DollarSign, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "kaoyan", label: "考研", icon: GraduationCap, href: "/kaoyan", desc: "院校情报、录取预测、导师评价、暗知识" },
  { id: "civil", label: "考公", icon: Landmark, href: "/civil-service", desc: "岗位情报、考公定位、暗知识" },
  { id: "career", label: "就业", icon: Briefcase, href: "/employment", desc: "公司情报、求职定位、就业数据" },
  { id: "salary", label: "薪资", icon: DollarSign, href: "/employment?tab=salary", desc: "各公司岗位薪资数据查询" },
  { id: "interview", label: "面经", icon: MessageSquare, href: "/interview", desc: "海量面试经验分享" },
];

export default function IntelPage() {
  const [activeTab, setActiveTab] = useState("kaoyan");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-800">情报中心</h1>
        <p className="text-ink-500 mt-1">查院校、查公司、查薪资、看面经，一站式获取决策所需信息</p>
      </div>
      <div className="flex gap-2 mb-6 border-b border-paper-300 pb-2 overflow-x-auto">
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
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {TABS.filter((t) => t.id === activeTab).map((tab) => (
          <Link
            key={tab.id}
            href={tab.href}
            className="col-span-full bg-white rounded-xl border border-paper-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 rounded-lg bg-brand-50 text-brand-600">
                <tab.icon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-semibold text-ink-800">{tab.label}</h2>
                <p className="text-sm text-ink-500">{tab.desc}</p>
              </div>
            </div>
            <p className="text-sm text-brand-600 font-medium mt-2">点击进入 {tab.label} 模块 →</p>
          </Link>
        ))}
      </div>
    </div>
  );
}