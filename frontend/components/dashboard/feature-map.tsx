"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Map as MapIcon,
  ChevronDown,
  ChevronUp,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ===== 新手引导增强 3：FeatureMap 功能地图 =====

interface FeatureEntry {
  name: string;
  href: string;
  desc: string;
  timing: string;
}

interface FeatureStage {
  stage: string;
  color: "blue" | "purple" | "orange" | "green" | "pink";
  features: FeatureEntry[];
}

/** 5 阶段功能地图 — 按用户旅程分类展示核心功能 */
const FEATURE_MAP: FeatureStage[] = [
  {
    stage: "认知 · 了解自己",
    color: "blue",
    features: [
      { name: "首次诊断", href: "/onboarding", desc: "告诉我你的方向", timing: "第 1 步" },
      { name: "职业测评", href: "/assessment", desc: "霍兰德 / MBTI / 大五 / DISC", timing: "第 2 步" },
      { name: "人生平衡轮", href: "/life-wheel", desc: "8 维度生活评估", timing: "任何时候" },
      { name: "技能树", href: "/skills", desc: "掌握的技能图谱", timing: "第 3 步" },
    ],
  },
  {
    stage: "探索 · 了解选项",
    color: "purple",
    features: [
      { name: "考研工具箱", href: "/kaoyan", desc: "院校 / 导师 / 分数线", timing: "考虑考研时" },
      { name: "考公中心", href: "/civil-service", desc: "岗位 / 备考 / 暗知识", timing: "考虑考公时" },
      { name: "就业中心", href: "/employment", desc: "公司 / 薪资 / 朝阳职业", timing: "考虑就业时" },
      { name: "面试经验", href: "/interview", desc: "面经 + 练习 + STAR 改写", timing: "求职准备" },
      { name: "失败案例库", href: "/failure-cases", desc: "别人的弯路是你的捷径", timing: "任何时候" },
    ],
  },
  {
    stage: "决策 · 做选择",
    color: "orange",
    features: [
      { name: "职业路径模拟器", href: "/career-simulator", desc: "试驾 + What-If 对比 + 90 天蓝图", timing: "第 4 步" },
      { name: "决策实验室", href: "/decision-lab", desc: "5 步结构化分析", timing: "第 5 步" },
      { name: "决策中心", href: "/decision-center", desc: "决策看板 + 路径冲突调解", timing: "第 6 步" },
      { name: "7 天微行动", href: "/micro-actions", desc: "不替你决定，让你自己发现", timing: "犹豫不决时" },
      { name: "家庭对话", href: "/family-dialogue", desc: "和父母沟通的脚手架", timing: "家庭冲突时" },
    ],
  },
  {
    stage: "行动 · 执行计划",
    color: "green",
    features: [
      { name: "职业规划", href: "/plans", desc: "计划 + 里程碑 + 日志", timing: "第 7 步" },
      { name: "学习计划", href: "/study-plans", desc: "AI 生成 + 手动创建", timing: "需要学习时" },
      { name: "人生设计", href: "/life-design", desc: "Sprint 目标 + 周回顾", timing: "任何时候" },
      { name: "时间线", href: "/timeline", desc: "记录重要事件", timing: "任何时候" },
    ],
  },
  {
    stage: "反思 · 复盘调整",
    color: "pink",
    features: [
      { name: "阶段复盘", href: "/retrospectives", desc: "周复盘 + 模板 + AI 辅助", timing: "第 8 步" },
      { name: "成长档案", href: "/growth/archive", desc: "成长轨迹总览", timing: "任何时候" },
      { name: "成就墙", href: "/achievements", desc: "徽章 + 等级 + 导出", timing: "任何时候" },
      { name: "上岸报告", href: "/outcome-report", desc: "分享你的上岸故事", timing: "上岸后" },
    ],
  },
];

const TOTAL_FEATURES = FEATURE_MAP.reduce((sum, s) => sum + s.features.length, 0);

const STAGE_COLOR: Record<
  FeatureStage["color"],
  { dot: string; chip: string; bar: string; ring: string }
> = {
  blue: {
    dot: "bg-blue-500",
    chip: "bg-blue-50 text-blue-700",
    bar: "bg-blue-400",
    ring: "ring-blue-100",
  },
  purple: {
    dot: "bg-purple-500",
    chip: "bg-purple-50 text-purple-700",
    bar: "bg-purple-400",
    ring: "ring-purple-100",
  },
  orange: {
    dot: "bg-orange-500",
    chip: "bg-orange-50 text-orange-700",
    bar: "bg-orange-400",
    ring: "ring-orange-100",
  },
  green: {
    dot: "bg-emerald-500",
    chip: "bg-emerald-50 text-emerald-700",
    bar: "bg-emerald-400",
    ring: "ring-emerald-100",
  },
  pink: {
    dot: "bg-pink-500",
    chip: "bg-pink-50 text-pink-700",
    bar: "bg-pink-400",
    ring: "ring-pink-100",
  },
};

/** 功能地图：5 阶段横向（移动端纵向）排列，折叠式 */
export function FeatureMap() {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <section className="card p-5 animate-fade-in">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <MapIcon className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h2 className="font-display font-semibold text-ink-800">
              功能地图
              <span className="ml-2 text-xs font-normal text-ink-400">
                · {TOTAL_FEATURES} 个核心功能
              </span>
            </h2>
            <p className="text-xs text-ink-400">按你的节奏来，不用全部做完</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "展开功能地图" : "折叠功能地图"}
          className="shrink-0 inline-flex items-center gap-1 rounded-lg border border-paper-200 px-2.5 py-1.5 text-xs text-ink-600 hover:bg-paper-100 transition-colors"
        >
          {collapsed ? (
            <>
              展开 <ChevronDown className="h-3.5 w-3.5" />
            </>
          ) : (
            <>
              收起 <ChevronUp className="h-3.5 w-3.5" />
            </>
          )}
        </button>
      </div>

      {!collapsed && (
        <>
          {/* 阶段轨道 */}
          <div className="mt-5 grid gap-4 lg:grid-cols-5">
            {FEATURE_MAP.map((stage) => {
              const color = STAGE_COLOR[stage.color];
              return (
                <div
                  key={stage.stage}
                  className={cn(
                    "rounded-xl border border-paper-200 bg-white p-3 ring-1",
                    color.ring,
                  )}
                >
                  <div className="mb-3 flex items-center gap-2">
                    <span className={cn("h-2.5 w-2.5 rounded-full", color.dot)} />
                    <h3 className="text-sm font-semibold text-ink-800">
                      {stage.stage}
                    </h3>
                  </div>
                  <ul className="space-y-2">
                    {stage.features.map((f) => (
                      <li key={f.href}>
                        <Link
                          href={f.href}
                          className="group block rounded-lg border border-paper-100 bg-paper-50/40 px-2.5 py-2 transition-all hover:border-brand-300 hover:bg-brand-50/40 hover:shadow-card"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-xs font-semibold text-ink-800 truncate group-hover:text-brand-700">
                              {f.name}
                            </p>
                            <ChevronRight className="h-3 w-3 shrink-0 text-ink-300 group-hover:text-brand-500" />
                          </div>
                          <p className="mt-0.5 text-[11px] text-ink-500 leading-relaxed line-clamp-2">
                            {f.desc}
                          </p>
                          <span
                            className={cn(
                              "mt-1.5 inline-block rounded px-1.5 py-0.5 text-[10px] font-medium",
                              color.chip,
                            )}
                          >
                            {f.timing}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>

          <p className="mt-4 text-center text-xs italic text-ink-400">
            不用全部做完，按你的节奏来
          </p>
        </>
      )}
    </section>
  );
}
