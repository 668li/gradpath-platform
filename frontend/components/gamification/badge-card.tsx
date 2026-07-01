"use client";

import {
  Compass,
  Sparkles,
  Wrench,
  ClipboardList,
  Users,
  Briefcase,
  Star,
  Crown,
  Check,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Badge as BadgeType } from "@/types";

/** badge.icon 字段到 lucide 图标的映射 */
const ICON_MAP: Record<string, LucideIcon> = {
  compass: Compass,
  sparkles: Sparkles,
  wrench: Wrench,
  clipboard: ClipboardList,
  users: Users,
  briefcase: Briefcase,
  star: Star,
  crown: Crown,
};

interface BadgeCardProps {
  badge: BadgeType;
  earned: boolean;
}

/**
 * 单个徽章卡片。
 * earned 为 true 时高亮显示（brand 配色 + 勾选标记），
 * 否则以灰度 + 半透明展示锁定状态。
 */
export function BadgeCard({ badge, earned }: BadgeCardProps) {
  const Icon = ICON_MAP[badge.icon] ?? Star;

  return (
    <div
      className={cn(
        "relative rounded-xl border p-4 text-center transition-all",
        earned
          ? "border-brand-200 bg-brand-50"
          : "border-slate-200 bg-slate-50 opacity-50 grayscale",
      )}
    >
      {earned && (
        <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white">
          <Check className="h-3 w-3" />
        </span>
      )}
      <div
        className={cn(
          "mx-auto flex h-12 w-12 items-center justify-center rounded-full",
          earned ? "bg-brand-100 text-brand-600" : "bg-slate-200 text-slate-400",
        )}
      >
        <Icon className="h-6 w-6" />
      </div>
      <p
        className={cn(
          "mt-2 text-sm font-medium",
          earned ? "text-slate-800" : "text-slate-500",
        )}
      >
        {badge.name}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-slate-500">
        {badge.description}
      </p>
    </div>
  );
}
