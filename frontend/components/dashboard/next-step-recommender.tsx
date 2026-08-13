"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  Compass,
  Brain,
  Route,
  Target,
  ClipboardList,
  Lightbulb,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// ===== 新手引导增强 2：NextStepRecommender 智能推荐 =====

export interface UserState {
  hasOnboarding: boolean;
  hasAssessment: boolean;
  hasSimulation: boolean;
  hasDecision: boolean;
  hasPlan: boolean;
}

type RecommendationPriority = "high" | "medium" | "low";

interface Recommendation {
  priority: RecommendationPriority;
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

/** 基于用户当前状态计算推荐 */
function recommendNextSteps(state: UserState): Recommendation[] {
  const recs: Recommendation[] = [];

  // 1. 没做 onboarding → 高优先级
  if (!state.hasOnboarding) {
    recs.push({
      priority: "high",
      title: "先告诉我你的方向",
      description: "完成首次诊断，我们会为你定制体验",
      href: "/onboarding",
      icon: Compass,
    });
  }

  // 2. 做了 onboarding 没做测评 → 高优先级
  if (state.hasOnboarding && !state.hasAssessment) {
    recs.push({
      priority: "high",
      title: "做测评了解自己",
      description: "霍兰德 + MBTI + 大五 + DISC，15 分钟看清你的职业基因",
      href: "/assessment",
      icon: Brain,
    });
  }

  // 3. 做了测评没做模拟 → 高优先级
  if (state.hasAssessment && !state.hasSimulation) {
    recs.push({
      priority: "high",
      title: "看看你的路径",
      description: "基于测评结果，模拟你的职业路径",
      href: "/career-simulator?from=recommend",
      icon: Route,
    });
  }

  // 4. 做了模拟没做决策分析 → 中优先级
  if (state.hasSimulation && !state.hasDecision) {
    recs.push({
      priority: "medium",
      title: "深度分析这条路径",
      description: "5 步结构化分析，把直觉变成决策",
      href: "/decision-lab?from=recommend",
      icon: Target,
    });
  }

  // 5. 做了决策没做计划 → 中优先级
  if (state.hasDecision && !state.hasPlan) {
    recs.push({
      priority: "medium",
      title: "制定行动计划",
      description: "把决策变成可执行的步骤",
      href: "/plans?from=recommend",
      icon: ClipboardList,
    });
  }

  // 6. 通用推荐（始终补一条到 3 条）
  if (recs.length < 3) {
    recs.push({
      priority: "low",
      title: "看看别人的弯路",
      description: "失败案例库，避免重复踩坑",
      href: "/failure-cases",
      icon: Lightbulb,
    });
  }

  return recs.slice(0, 3);
}

const PRIORITY_STYLE: Record<
  RecommendationPriority,
  { bg: string; border: string; text: string; label: string; badge: string }
> = {
  high: {
    bg: "bg-red-50/40",
    border: "border-red-200",
    text: "text-red-700",
    label: "现在就做",
    badge: "bg-red-100 text-red-700",
  },
  medium: {
    bg: "bg-blue-50/40",
    border: "border-blue-200",
    text: "text-blue-700",
    label: "建议近期",
    badge: "bg-blue-100 text-blue-700",
  },
  low: {
    bg: "bg-paper-50",
    border: "border-paper-200",
    text: "text-ink-500",
    label: "有空看看",
    badge: "bg-paper-100 text-ink-500",
  },
};

/** 智能下一步推荐：基于用户状态推荐 1-3 个行动 */
export function NextStepRecommender({ state }: { state: UserState }) {
  const recs = useMemo(() => recommendNextSteps(state), [state]);

  if (recs.length === 0) return null;

  return (
    <section className="card p-5 animate-fade-in">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-50 text-purple-600">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <h2 className="font-display font-semibold text-ink-800">为你推荐</h2>
          <p className="text-xs text-ink-400">基于你的进度，推荐下一步</p>
        </div>
      </div>

      <ul className="space-y-2">
        {recs.map((rec, idx) => {
          const style = PRIORITY_STYLE[rec.priority];
          const Icon = rec.icon;
          return (
            <li
              key={`rec-${idx}-${rec.href}`}
              className={cn(
                "flex items-start gap-3 rounded-lg border px-3 py-3 transition-colors",
                style.bg,
                style.border,
              )}
            >
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                  style.badge,
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-ink-800 truncate">
                    {rec.title}
                  </p>
                  <span
                    className={cn(
                      "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                      style.badge,
                    )}
                  >
                    {style.label}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-ink-500 leading-relaxed">
                  {rec.description}
                </p>
              </div>
              <Link
                href={rec.href}
                className={cn(
                  "shrink-0 inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                  rec.priority === "high"
                    ? "bg-red-600 text-white hover:bg-red-700"
                    : rec.priority === "medium"
                      ? "bg-brand-600 text-white hover:bg-brand-700"
                      : "bg-ink-200 text-ink-700 hover:bg-ink-300",
                )}
              >
                去完成 <ArrowRight className="h-3 w-3" />
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
