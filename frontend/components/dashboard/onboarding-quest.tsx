"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Compass,
  Brain,
  Route,
  Target,
  Network,
  ClipboardList,
  ListTodo,
  Lightbulb,
  Footprints,
  Trophy,
  PartyPopper,
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// ===== 新手引导增强 1：OnboardingQuest 任务清单 =====

interface QuestTask {
  id: string;
  title: string;
  description: string;
  href: string;
  score: number;
  icon: LucideIcon;
}

/** 10 个新手任务，按用户旅程排序 */
const QUEST_TASKS: QuestTask[] = [
  {
    id: "onboarding",
    title: "完成首次诊断",
    description: "告诉我你的方向，3 分钟定制你的体验",
    href: "/onboarding",
    score: 5,
    icon: Compass,
  },
  {
    id: "assessment",
    title: "做一次职业测评",
    description: "霍兰德 / MBTI / 大五 / DISC，看清你的职业基因",
    href: "/assessment",
    score: 10,
    icon: Brain,
  },
  {
    id: "career-simulator",
    title: "查看职业路径模拟",
    description: "10 年路径推演，看到不同选择的长程结果",
    href: "/career-simulator",
    score: 10,
    icon: Route,
  },
  {
    id: "test-drive",
    title: "试驾一日体验",
    description: "在模拟器里过一天你心仪职业的真实日常",
    href: "/career-simulator#test-drive",
    score: 10,
    icon: Target,
  },
  {
    id: "what-if",
    title: "多路径 What-If 对比",
    description: "并行对比 2-3 条路径，量化差异",
    href: "/career-simulator#what-if",
    score: 10,
    icon: Network,
  },
  {
    id: "decision-lab",
    title: "做一次决策分析",
    description: "5 步结构化分析，把直觉变成可追溯决策",
    href: "/decision-lab",
    score: 15,
    icon: ClipboardList,
  },
  {
    id: "plans",
    title: "创建行动计划",
    description: "把决策拆成里程碑与可执行步骤",
    href: "/plans",
    score: 15,
    icon: ListTodo,
  },
  {
    id: "failure-cases",
    title: "阅读失败案例",
    description: "别人的弯路，是你最便宜的捷径",
    href: "/failure-cases",
    score: 5,
    icon: Lightbulb,
  },
  {
    id: "micro-actions",
    title: "开始 7 天微行动",
    description: "不替你决定，让你自己发现答案",
    href: "/micro-actions",
    score: 10,
    icon: Footprints,
  },
  {
    id: "retrospectives",
    title: "完成一次复盘",
    description: "周复盘 + 模板 + AI 辅助，沉淀你的成长",
    href: "/retrospectives",
    score: 10,
    icon: ClipboardList,
  },
];

const QUEST_STORAGE_KEY = "gradpath_onboarding_quest";

/** 读取 localStorage 中已完成的任务 id 集合 */
function getQuestProgress(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const stored = localStorage.getItem(QUEST_STORAGE_KEY);
    const arr = stored ? (JSON.parse(stored) as string[]) : [];
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

/** 写入已完成任务 id 集合 */
function saveQuestProgress(completed: Set<string>) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(QUEST_STORAGE_KEY, JSON.stringify([...completed]));
  } catch {
    // 静默失败：隐私模式或配额超限
  }
}

/** 新手任务清单：10 个任务，localStorage 存储进度，可折叠 */
export function OnboardingQuest() {
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [hydrated, setHydrated] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // 初次挂载：从 localStorage 读取
  useEffect(() => {
    setCompleted(getQuestProgress());
    setHydrated(true);
  }, []);

  // 全部完成时自动折叠
  useEffect(() => {
    if (hydrated && completed.size === QUEST_TASKS.length && !collapsed) {
      setCollapsed(true);
    }
  }, [hydrated, completed, collapsed]);

  const totalScore = QUEST_TASKS.reduce((sum, t) => sum + t.score, 0);
  const earnedScore = QUEST_TASKS
    .filter((t) => completed.has(t.id))
    .reduce((sum, t) => sum + t.score, 0);
  const completedCount = completed.size;
  const allDone = completedCount === QUEST_TASKS.length;
  const progressPercent = (completedCount / QUEST_TASKS.length) * 100;

  const toggleTask = (id: string) => {
    const next = new Set(completed);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setCompleted(next);
    saveQuestProgress(next);
  };

  return (
    <section className="card p-5 animate-fade-in">
      {/* 头部：标题 + 进度 + 折叠按钮 */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <Trophy className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h2 className="font-display font-semibold text-ink-800 flex items-center gap-2">
              新手任务
              {hydrated && allDone && (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                  已完成
                </span>
              )}
            </h2>
            <p className="text-xs text-ink-400">
              10 个核心任务，带你走完一遍完整旅程
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "展开任务清单" : "折叠任务清单"}
          className="shrink-0 rounded-lg p-1.5 text-ink-400 hover:bg-paper-100 hover:text-ink-600 transition-colors"
        >
          {collapsed ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* 进度条 + 总分 */}
      {!collapsed && (
        <>
          <div className="mt-4">
            <div className="mb-1.5 flex items-baseline justify-between text-xs">
              <span className="font-medium text-ink-600">
                已完成 {completedCount} / {QUEST_TASKS.length}
              </span>
              <span className="text-ink-500">
                <span className="font-semibold text-brand-600">{earnedScore}</span>
                <span className="text-ink-400"> / {totalScore} 分</span>
              </span>
            </div>
            <div className="h-2 rounded-full bg-paper-200 overflow-hidden">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-brand-400 to-emerald-400 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* 全部完成提示 */}
          {hydrated && allDone && (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700">
              <PartyPopper className="h-4 w-4" />
              <span>恭喜！你已掌握核心功能，继续探索更多吧</span>
            </div>
          )}

          {/* 任务列表 */}
          <ul className="mt-4 grid gap-2 md:grid-cols-2">
            {QUEST_TASKS.map((task, idx) => {
              const done = completed.has(task.id);
              const Icon = task.icon;
              return (
                <li key={task.id}>
                  <Link
                    href={task.href}
                    className={cn(
                      "group flex items-start gap-3 rounded-lg border px-3 py-2.5 transition-all hover:shadow-card",
                      done
                        ? "border-emerald-200 bg-emerald-50/40"
                        : "border-paper-200 bg-white hover:border-brand-300 hover:bg-brand-50/30",
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold",
                        done
                          ? "bg-emerald-500 text-white"
                          : "bg-paper-100 text-ink-500",
                      )}
                    >
                      {done ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : (
                        <span>{idx + 1}</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Icon
                          className={cn(
                            "h-3.5 w-3.5 shrink-0",
                            done ? "text-emerald-500" : "text-ink-400",
                          )}
                        />
                        <p
                          className={cn(
                            "text-sm font-medium truncate",
                            done
                              ? "text-ink-400 line-through"
                              : "text-ink-800",
                          )}
                        >
                          {task.title}
                        </p>
                      </div>
                      <p className="mt-0.5 text-xs text-ink-400 line-clamp-1">
                        {task.description}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                        done
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700",
                      )}
                    >
                      +{task.score}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>

          {/* 手动标记入口（用户可在不离开看板的情况下勾选最近完成的任务） */}
          <div className="mt-4 border-t border-paper-100 pt-3">
            <p className="mb-2 text-xs text-ink-400">
              手动标记完成状态（用于已做过但未通过页面触发的任务）：
            </p>
            <div className="flex flex-wrap gap-1.5">
              {QUEST_TASKS.map((task) => {
                const done = completed.has(task.id);
                return (
                  <button
                    key={`toggle-${task.id}`}
                    type="button"
                    onClick={() => toggleTask(task.id)}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] transition-colors",
                      done
                        ? "border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                        : "border-paper-200 bg-white text-ink-500 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {done ? (
                      <CheckCircle2 className="h-3 w-3" />
                    ) : (
                      <Circle className="h-3 w-3" />
                    )}
                    {task.title}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* 折叠时显示精简进度 */}
      {collapsed && (
        <div className="mt-3 flex items-center gap-3 text-sm">
          <div className="flex-1 min-w-0">
            <div className="h-1.5 rounded-full bg-paper-200 overflow-hidden">
              <div
                className="h-1.5 rounded-full bg-gradient-to-r from-brand-400 to-emerald-400 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
          <span className="shrink-0 text-xs text-ink-500">
            {completedCount}/{QUEST_TASKS.length} · {earnedScore} 分
          </span>
        </div>
      )}
    </section>
  );
}
