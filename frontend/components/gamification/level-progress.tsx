"use client";

import { cn } from "@/lib/utils";
import type { ProgressInfo } from "@/types";

interface LevelProgressProps {
  xp: number;
  level: number;
  levelName: string;
  progress: ProgressInfo;
  compact?: boolean;
}

/**
 * 等级进度环：SVG 圆形进度环 + 等级信息 + 经验进度条。
 * compact 模式下尺寸更小，适合在仪表盘卡片中预览。
 */
export function LevelProgress({
  xp,
  level,
  levelName,
  progress,
  compact = false,
}: LevelProgressProps) {
  const size = compact ? 80 : 128;
  const strokeWidth = compact ? 6 : 9;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedPercent = Math.max(0, Math.min(100, progress.percent));
  const offset = circumference * (1 - clampedPercent / 100);

  return (
    <div className={cn("flex items-center gap-4", compact && "gap-3")}>
      {/* 圆形进度环 */}
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="-rotate-90"
          aria-hidden="true"
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            className="text-slate-100"
            stroke="currentColor"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            className="text-brand-600 transition-all duration-500"
            stroke="currentColor"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cn(
              "font-bold leading-none text-brand-600",
              compact ? "text-lg" : "text-2xl",
            )}
          >
            Lv.{level}
          </span>
          {!compact && (
            <span className="mt-0.5 text-[10px] text-slate-400">等级</span>
          )}
        </div>
      </div>

      {/* 等级信息与进度条 */}
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "font-semibold text-slate-800 truncate",
            compact ? "text-sm" : "text-base",
          )}
        >
          {levelName}
        </p>
        <p
          className={cn(
            "text-slate-500",
            compact ? "text-xs" : "text-sm",
          )}
        >
          累计经验值{" "}
          <span className="font-semibold text-brand-600">{xp}</span> XP
        </p>

        {!compact ? (
          <div className="mt-2">
            <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
              <span>距下一级</span>
              <span>
                {progress.current} / {progress.needed} XP（{clampedPercent}%）
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand-600 transition-all duration-500"
                style={{ width: `${clampedPercent}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand-600 transition-all duration-500"
              style={{ width: `${clampedPercent}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
