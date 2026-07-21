"use client";

import { useState } from "react";
import { CheckCircle2, Flame, Sparkles, BookOpen, Zap } from "lucide-react";
import type { StreakStats } from "@/types";
import { streaksApi } from "@/lib/api/gamification";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/form-controls";

interface StreakActionsProps {
  stats: StreakStats;
  onCheckin: () => void;
}

export function StreakActions({ stats, onCheckin }: StreakActionsProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [completedMain, setCompletedMain] = useState(
    stats.today_active && stats.recent_records[0]?.activity_types?.includes("main")
  );
  const [completedMicro, setCompletedMicro] = useState(
    stats.today_active && stats.recent_records[0]?.activity_types?.includes("micro")
  );
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState("");

  const handleCheckin = async (type: "main" | "micro") => {
    setLoading(type);
    try {
      const res = await streaksApi.checkin({
        action_type: type,
        action_detail: type === "main" ? "完成今日主行动" : "完成今日微行动",
      });
      if (type === "main") setCompletedMain(true);
      else setCompletedMicro(true);

      setFeedbackMsg(
        type === "main"
          ? `连胜 +1！主行动完成，获得 ${res.xp_earned}XP`
          : `微行动完成！获得 ${res.xp_earned}XP`
      );
      setShowFeedback(true);
      setTimeout(() => setShowFeedback(false), 3000);
      onCheckin();
    } finally {
      setLoading(null);
    }
  };

  const handleRedeem = async () => {
    setLoading("redeem");
    try {
      const res = await streaksApi.redeem();
      setFeedbackMsg(res.message);
      setShowFeedback(true);
      setTimeout(() => setShowFeedback(false), 3000);
      onCheckin();
    } finally {
      setLoading(null);
    }
  };

  const todayDone = completedMain && completedMicro;
  const todayPartial = completedMain || completedMicro;

  return (
    <div className="card overflow-hidden animate-fade-in">
      <h3 className="mb-3 font-display text-sm font-semibold text-ink-700">
        今日行动
      </h3>

      {/* 完成反馈 */}
      {showFeedback && (
        <div className="mb-3 flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 text-sm font-medium text-brand-700 animate-fade-in">
          <Sparkles className="h-4 w-4" />
          {feedbackMsg}
        </div>
      )}

      {/* 双行动卡片 */}
      <div className="flex flex-col gap-2">
        {/* 主行动 */}
        <div
          className={cn(
            "flex items-center gap-3 rounded-lg border p-3 transition-all",
            completedMain
              ? "border-brand-200 bg-brand-50/50"
              : "border-paper-200 bg-paper-50 hover:border-brand-200"
          )}
        >
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
              completedMain
                ? "bg-brand-100 text-brand-600"
                : "bg-brand-50 text-brand-500"
            )}
          >
            <BookOpen className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-700">主行动</p>
            <p className="text-xs text-ink-400">
              今日核心任务 · 预计20-30分钟
            </p>
          </div>
          {completedMain ? (
            <CheckCircle2 className="h-5 w-5 shrink-0 text-brand-500" />
          ) : (
            <Button
              variant="primary"
              size="sm"
              loading={loading === "main"}
              onClick={() => handleCheckin("main")}
            >
              完成
            </Button>
          )}
        </div>

        {/* 微行动 */}
        <div
          className={cn(
            "flex items-center gap-3 rounded-lg border p-3 transition-all",
            completedMicro
              ? "border-amber-200 bg-amber-50/50"
              : "border-paper-200 bg-paper-50 hover:border-amber-200"
          )}
        >
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
              completedMicro
                ? "bg-amber-100 text-amber-600"
                : "bg-amber-50 text-amber-500"
            )}
          >
            <Zap className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-700">微行动</p>
            <p className="text-xs text-ink-400">
              看一条暗知识 / 补一条档案 · 预计5分钟
            </p>
          </div>
          {completedMicro ? (
            <CheckCircle2 className="h-5 w-5 shrink-0 text-amber-500" />
          ) : (
            <Button
              variant="secondary"
              size="sm"
              loading={loading === "micro"}
              onClick={() => handleCheckin("micro")}
            >
              完成
            </Button>
          )}
        </div>
      </div>

      {/* 全部完成 */}
      {todayDone && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm font-medium text-green-700">
          <Flame className="h-4 w-4" />
          今日行动全部完成！连胜 +1
        </div>
      )}

      {/* 回赎按钮 */}
      {stats.redeem_available && !todayDone && (
        <div className="mt-3">
          <Button
            variant="secondary"
            size="sm"
            className="w-full gap-1.5 border-purple-200 text-purple-700 hover:bg-purple-50"
            loading={loading === "redeem"}
            onClick={handleRedeem}
          >
            <Flame className="h-3.5 w-3.5" />
            双倍行动日完成！回赎断签
          </Button>
        </div>
      )}
    </div>
  );
}