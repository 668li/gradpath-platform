"use client";

import { Target } from "lucide-react";
import { cn } from "@/lib/utils";

// ===== Career Fit Score 活档案计算 =====

export interface FitScoreInput {
  assessmentCount: number;
  skillsCount: number;
  decisionsCount: number;
  completedMilestones: number;
  retrospectivesCount: number;
}

export interface FitScoreResult {
  total: number;
  dimensions: { key: string; label: string; score: number; max: number; raw: number }[];
}

/** 综合职业匹配指数：5 维度加权，每维满分 20，总分 100 */
export function calculateCareerFitScore(input: FitScoreInput): FitScoreResult {
  const cap = (v: number, max: number) => Math.min(v, max);
  const dimAssessment = { key: "assessment", label: "测评完成", score: cap(input.assessmentCount * 5, 20), max: 20, raw: input.assessmentCount };
  const dimSkills = { key: "skills", label: "技能掌握", score: cap(input.skillsCount * 2, 20), max: 20, raw: input.skillsCount };
  const dimDecisions = { key: "decisions", label: "决策记录", score: cap(input.decisionsCount * 5, 20), max: 20, raw: input.decisionsCount };
  const dimPlans = { key: "plans", label: "行动计划", score: cap(input.completedMilestones * 3, 20), max: 20, raw: input.completedMilestones };
  const dimRetros = { key: "retros", label: "复盘次数", score: cap(input.retrospectivesCount * 4, 20), max: 20, raw: input.retrospectivesCount };
  const total = dimAssessment.score + dimSkills.score + dimDecisions.score + dimPlans.score + dimRetros.score;
  return { total, dimensions: [dimAssessment, dimSkills, dimDecisions, dimPlans, dimRetros] };
}

/** 分数 → 等级标签 */
export function getFitLevel(score: number): { label: string; color: string } {
  if (score >= 85) return { label: "准备就绪", color: "text-emerald-600" };
  if (score >= 70) return { label: "接近就绪", color: "text-brand-600" };
  if (score >= 50) return { label: "进阶中", color: "text-blue-600" };
  if (score >= 30) return { label: "起步中", color: "text-amber-600" };
  return { label: "探索中", color: "text-ink-500" };
}

/** 圆形进度条 + 5 维度小进度条 */
export function CareerFitScoreCard({
  score,
  lastUpdatedDays,
}: {
  score: FitScoreResult;
  lastUpdatedDays: number | null;
}) {
  const level = getFitLevel(score.total);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score.total / 100) * circumference;

  return (
    <section className="card p-5 animate-fade-in">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
          <Target className="h-4 w-4" />
        </div>
        <h2 className="font-display font-semibold text-ink-800">职业匹配指数</h2>
        <span className="text-xs text-ink-400">活档案 · 随你的行动自动更新</span>
      </div>

      <div className="flex flex-col items-center gap-5 md:flex-row md:items-start">
        {/* 圆形进度条 */}
        <div className="relative shrink-0">
          <svg width={130} height={130} className="-rotate-90">
            <circle
              cx={65}
              cy={65}
              r={radius}
              fill="none"
              stroke="#e2e8f0"
              strokeWidth={10}
            />
            <circle
              cx={65}
              cy={65}
              r={radius}
              fill="none"
              stroke="url(#fitGradient)"
              strokeWidth={10}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className="transition-all duration-700"
            />
            <defs>
              <linearGradient id="fitGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-3xl font-bold text-ink-800">
              {score.total}
            </span>
            <span className="text-xs text-ink-400">/ 100</span>
          </div>
        </div>

        {/* 等级 + 更新信息 */}
        <div className="flex-1 min-w-0 space-y-3">
          <div>
            <span className={cn("font-display text-lg font-bold", level.color)}>
              {level.label}
            </span>
          </div>
          <p className="text-xs text-ink-400">
            上次更新：
            {lastUpdatedDays === null
              ? "尚未开始"
              : lastUpdatedDays === 0
                ? "今天"
                : `${lastUpdatedDays} 天前`}
          </p>
          <p className="text-xs text-ink-400 italic">
            每次你完成行动，分数会自动更新
          </p>
        </div>
      </div>

      {/* 各维度小进度条 */}
      <div className="mt-5 grid grid-cols-2 gap-x-5 gap-y-3 md:grid-cols-5">
        {score.dimensions.map((dim) => (
          <div key={dim.key}>
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-xs text-ink-500">{dim.label}</span>
              <span className="text-xs font-medium text-ink-700">
                {dim.score}/{dim.max}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-paper-200">
              <div
                className="h-1.5 rounded-full bg-brand-500 transition-all duration-500"
                style={{ width: `${(dim.score / dim.max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
